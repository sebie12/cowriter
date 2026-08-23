import unittest
from unittest.mock import patch

from flask import Flask

from backend.blueprints.chat import chat_bp
from backend.blueprints.provider_connections import provider_connections_bp
from backend.blueprints.providers import providers_bp
from backend.database import AuthMethod, Provider, ProviderConnection, db
from backend.database.catalog import ensure_provider_catalog
from backend.llm import ChatResult, ChatService, ProviderConfig


class OllamaRouteTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = Flask(__name__)
        cls.app.config.update(
            SQLALCHEMY_DATABASE_URI="sqlite:///:memory:",
            SQLALCHEMY_TRACK_MODIFICATIONS=False,
            TESTING=True,
        )
        db.init_app(cls.app)
        cls.app.extensions["chat_service"] = ChatService(
            connection_lookup=lambda connection_id: db.session.get(ProviderConnection, connection_id),
        )
        cls.app.register_blueprint(provider_connections_bp)
        cls.app.register_blueprint(providers_bp)
        cls.app.register_blueprint(chat_bp)

        with cls.app.app_context():
            db.create_all()
            ensure_provider_catalog(db)

    @classmethod
    def tearDownClass(cls):
        with cls.app.app_context():
            db.session.remove()
            db.drop_all()

    def setUp(self):
        with self.app.app_context():
            ProviderConnection.query.delete()
            db.session.commit()

    def create_ollama_connection(self):
        with self.app.app_context():
            auth_method = AuthMethod.query.filter_by(method_name="local").one()
            connection = ProviderConnection(
                provider="ollama",
                account_id="ollama-local",
                account_label="Local Ollama",
                endpoint_url="http://127.0.0.1:11434",
                auth_method_id=auth_method.id,
                status="connected",
            )
            db.session.add(connection)
            db.session.commit()
            return connection.id

    def create_openai_connection(self):
        with self.app.app_context():
            auth_method = AuthMethod.query.filter_by(method_name="api_key").one()
            connection = ProviderConnection(
                provider="openai",
                account_id="openai-api-key-test",
                account_label="OpenAI test key",
                auth_method_id=auth_method.id,
                status="connected",
            )
            db.session.add(connection)
            db.session.commit()
            return connection.id

    def test_catalog_and_connection_contract(self):
        client = self.app.test_client()
        providers = client.get("/api/providers/").get_json()
        ollama = next(provider for provider in providers if provider["id"] == "ollama")
        self.assertEqual(ollama["auth_methods"], ["local"])
        self.assertTrue(ollama["chat_supported"])

        with patch(
            "backend.auth.providers.Ollama.OllamaProvider.validate_connection",
            return_value="http://127.0.0.1:11434",
        ):
            response = client.post(
                "/api/providers/ollama/connect",
                json={
                    "auth_method": "local",
                    "server_url": "http://127.0.0.1:11434",
                },
            )

        self.assertEqual(response.status_code, 201)
        connection = response.get_json()
        self.assertEqual(connection["provider"], "ollama")
        self.assertEqual(connection["auth_method"], "local")
        self.assertEqual(connection["endpoint_url"], "http://127.0.0.1:11434")
        self.assertEqual(connection["status"], "connected")

    def test_catalog_repairs_case_variant_records(self):
        with self.app.app_context():
            duplicate_method = AuthMethod(method_name="Local")
            duplicate_provider = Provider(name="ollama", auth_methods=[duplicate_method])
            db.session.add_all([duplicate_method, duplicate_provider])
            db.session.flush()
            connection = ProviderConnection(
                provider="ollama",
                account_id="legacy-ollama",
                account_label="Legacy Ollama",
                auth_method_id=duplicate_method.id,
                status="connected",
            )
            db.session.add(connection)
            db.session.commit()

            ensure_provider_catalog(db)
            db.session.refresh(connection)

            self.assertEqual(connection.auth_method.method_name, "local")
            self.assertEqual(
                sum(provider.name.lower() == "ollama" for provider in Provider.query.all()),
                1,
            )

    def test_lists_models_for_connection(self):
        connection_id = self.create_ollama_connection()

        with patch(
            "backend.auth.providers.Ollama.OllamaProvider.list_models",
            return_value=["gemma3:latest", "qwen3:8b"],
        ) as list_models:
            response = self.app.test_client().get(
                f"/provider-connections/{connection_id}/models",
            )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.get_json()["models"], [
            {"id": "gemma3:latest", "name": "gemma3:latest"},
            {"id": "qwen3:8b", "name": "qwen3:8b"},
        ])
        list_models.assert_called_once_with(
            ProviderConfig(endpoint_url="http://127.0.0.1:11434", credentials={}),
        )

    def test_connects_openai_and_stores_api_key(self):
        client = self.app.test_client()
        with (
            patch("backend.auth.providers.Openai.OpenAIProvider.validate_api_key"),
            patch("backend.blueprints.providers.credential_store.save") as save_credentials,
        ):
            response = client.post(
                "/api/providers/openai/connect",
                json={"auth_method": "api_key", "api_key": "test-key"},
            )

        self.assertEqual(response.status_code, 201)
        self.assertEqual(response.get_json()["provider"], "openai")
        account_id = response.get_json()["account_id"]
        save_credentials.assert_called_once_with(
            "openai",
            account_id,
            {"api_key": "test-key"},
        )

    def test_lists_openai_models_through_chat_service(self):
        connection_id = self.create_openai_connection()
        service = self.app.extensions["chat_service"]

        with (
            patch.object(
                service.credential_store,
                "get_many",
                return_value={"api_key": "test-key"},
            ),
            patch(
                "backend.auth.providers.Openai.OpenAIProvider.list_models",
                return_value=["gpt-test"],
            ) as list_models,
        ):
            response = self.app.test_client().get(
                f"/provider-connections/{connection_id}/models",
            )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.get_json()["provider"], "openai")
        self.assertEqual(response.get_json()["models"], [
            {"id": "gpt-test", "name": "gpt-test"},
        ])
        list_models.assert_called_once_with(
            ProviderConfig(credentials={"api_key": "test-key"}),
        )

    def test_chat_uses_selected_connection_model_and_history(self):
        connection_id = self.create_ollama_connection()
        messages = [
            {"role": "user", "content": "First question"},
            {"role": "assistant", "content": "First answer"},
            {"role": "user", "content": "Follow-up"},
        ]

        with patch(
            "backend.auth.providers.Ollama.OllamaProvider.chat",
            return_value=ChatResult(message="Ollama answer"),
        ) as chat:
            response = self.app.test_client().post(
                "/api/chat",
                json={
                    "connection_id": connection_id,
                    "provider": "ollama",
                    "model": "qwen3:8b",
                    "message": "Follow-up",
                    "system_prompt": "Be helpful.",
                    "history": messages[:-1],
                },
            )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.get_json(), {"message": "Ollama answer"})
        request, config = chat.call_args.args
        self.assertEqual(request.provider, "ollama")
        self.assertEqual(request.model, "qwen3:8b")
        self.assertEqual(request.message, "Follow-up")
        self.assertEqual(request.system_prompt, "Be helpful.")
        self.assertEqual(request.history, tuple(messages[:-1]))
        self.assertEqual(config.endpoint_url, "http://127.0.0.1:11434")

    def test_chat_rejects_invalid_payload(self):
        response = self.app.test_client().post(
            "/api/chat",
            json={"connection_id": True, "provider": "", "model": "", "message": ""},
        )

        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.get_json(), {"error": "connection_id is required."})


if __name__ == "__main__":
    unittest.main()
