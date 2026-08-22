from flask_admin.contrib.sqla import ModelView


class ProviderModelView(ModelView):
    column_list = ["name", "description", "auth_methods"]
    form_columns = ["name", "description", "auth_methods"]


class AuthMethodModelView(ModelView):
    column_list = ["method_name", "description"]
    form_columns = ["method_name", "description"]
