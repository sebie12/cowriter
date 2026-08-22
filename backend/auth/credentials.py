from collections.abc import Iterable, Mapping

import keyring

SERVICE_NAME = "cowriter"


class CredentialStore:
    def __init__(self, service_name: str = SERVICE_NAME):
        self.service_name = service_name

    def save(
        self,
        provider: str,
        account_id: str,
        credentials: Mapping[str, str],
    ) -> None:
        provider = self._require_value("provider", provider)
        account_id = self._require_value("account_id", account_id)
        if not credentials:
            raise ValueError("credentials must not be empty")

        previous_values: dict[str, str | None] = {}
        saved_fields: list[str] = []
        try:
            for field, value in credentials.items():
                field = self._require_value("credential field", field)
                value = self._require_value(field, value)
                credential_name = self._credential_name(provider, account_id, field)
                previous_values[field] = keyring.get_password(
                    self.service_name,
                    credential_name,
                )
                keyring.set_password(
                    self.service_name,
                    credential_name,
                    value,
                )
                saved_fields.append(field)
        except Exception:
            for field in saved_fields:
                previous_value = previous_values[field]
                if previous_value is None:
                    self._delete(provider, account_id, field)
                else:
                    keyring.set_password(
                        self.service_name,
                        self._credential_name(provider, account_id, field),
                        previous_value,
                    )
            raise

    def get(self, provider: str, account_id: str, field: str) -> str | None:
        return keyring.get_password(
            self.service_name,
            self._credential_name(
                self._require_value("provider", provider),
                self._require_value("account_id", account_id),
                self._require_value("credential field", field),
            ),
        )

    def get_many(
        self,
        provider: str,
        account_id: str,
        fields: Iterable[str],
    ) -> dict[str, str]:
        credentials: dict[str, str] = {}
        for field in fields:
            value = self.get(provider, account_id, field)
            if value is not None:
                credentials[field] = value

        return credentials

    def delete(self, provider: str, account_id: str, fields: Iterable[str]) -> None:
        provider = self._require_value("provider", provider)
        account_id = self._require_value("account_id", account_id)

        for field in fields:
            self._delete(
                provider,
                account_id,
                self._require_value("credential field", field),
            )

    def _delete(self, provider: str, account_id: str, field: str) -> None:
        try:
            keyring.delete_password(
                self.service_name,
                self._credential_name(provider, account_id, field),
            )
        except keyring.errors.PasswordDeleteError:
            pass

    def _credential_name(self, provider: str, account_id: str, field: str) -> str:
        return f"{provider}:{account_id}:{field}"

    def _require_value(self, name: str, value: str) -> str:
        if not isinstance(value, str) or not value.strip():
            raise ValueError(f"{name} must be a non-empty string")

        return value.strip()
