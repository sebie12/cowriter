from .models import AuthMethod, Provider, ProviderConnection


def ensure_ollama_catalog(db) -> None:
    local_methods = [
        method
        for method in AuthMethod.query.all()
        if method.method_name.strip().lower() == "local"
    ]
    canonical_method = next(
        (method for method in local_methods if method.method_name == "local"),
        local_methods[0] if local_methods else None,
    )

    if canonical_method is None:
        canonical_method = AuthMethod(
            method_name="local",
            description="Connect to a model server running on this computer.",
        )
        db.session.add(canonical_method)
    else:
        canonical_method.method_name = "local"
        canonical_method.description = "Connect to a model server running on this computer."

    for duplicate in local_methods:
        if duplicate is canonical_method:
            continue
        ProviderConnection.query.filter_by(auth_method_id=duplicate.id).update(
            {"auth_method_id": canonical_method.id},
            synchronize_session=False,
        )
        for provider in list(duplicate.providers):
            if canonical_method not in provider.auth_methods:
                provider.auth_methods.append(canonical_method)
            provider.auth_methods.remove(duplicate)
        db.session.delete(duplicate)

    ollama_providers = [
        provider
        for provider in Provider.query.all()
        if provider.name.strip().lower() == "ollama"
    ]
    ollama = next(
        (provider for provider in ollama_providers if provider.name == "Ollama"),
        ollama_providers[0] if ollama_providers else None,
    )
    if ollama is None:
        ollama = Provider(name="Ollama")
        db.session.add(ollama)

    ollama.name = "Ollama"
    ollama.description = "Connect to an Ollama server running on this computer."
    ollama.auth_methods = [canonical_method]
    for duplicate in ollama_providers:
        if duplicate is not ollama:
            db.session.delete(duplicate)
    db.session.commit()


def ensure_openai_catalog(db) -> None:
    api_key_methods = [
        method
        for method in AuthMethod.query.all()
        if method.method_name.strip().lower().replace(" ", "_").replace("-", "_")
        in {"api_key", "apikey"}
    ]
    canonical_method = next(
        (method for method in api_key_methods if method.method_name == "api_key"),
        api_key_methods[0] if api_key_methods else None,
    )

    if canonical_method is None:
        canonical_method = AuthMethod(
            method_name="api_key",
            description="Connect using a provider API key.",
        )
        db.session.add(canonical_method)
    else:
        canonical_method.method_name = "api_key"
        canonical_method.description = "Connect using a provider API key."

    for duplicate in api_key_methods:
        if duplicate is canonical_method:
            continue
        ProviderConnection.query.filter_by(auth_method_id=duplicate.id).update(
            {"auth_method_id": canonical_method.id},
            synchronize_session=False,
        )
        for provider in list(duplicate.providers):
            if canonical_method not in provider.auth_methods:
                provider.auth_methods.append(canonical_method)
            provider.auth_methods.remove(duplicate)
        db.session.delete(duplicate)

    openai_providers = [
        provider
        for provider in Provider.query.all()
        if provider.name.strip().lower() == "openai"
    ]
    openai = next(
        (provider for provider in openai_providers if provider.name == "OpenAI"),
        openai_providers[0] if openai_providers else None,
    )
    if openai is None:
        openai = Provider(name="OpenAI")
        db.session.add(openai)

    openai.name = "OpenAI"
    openai.description = "Connect to OpenAI using an API key."
    openai.auth_methods = [canonical_method]
    for duplicate in openai_providers:
        if duplicate is not openai:
            db.session.delete(duplicate)
    db.session.commit()


def ensure_provider_catalog(db) -> None:
    ensure_ollama_catalog(db)
    ensure_openai_catalog(db)
