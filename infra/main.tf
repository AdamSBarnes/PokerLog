data "azurerm_client_config" "current" {}

data "azuread_user" "current_user" {
  object_id = data.azurerm_client_config.current.object_id
}
resource "azurerm_resource_group" "rg" {
  name     = "poker-stats"
  location = var.region
}

resource "azurerm_app_service_plan" "asp" {
  name                = "service-plan"
  location            = azurerm_resource_group.rg.location
  resource_group_name = azurerm_resource_group.rg.name
  sku {
    size = "F1"
    tier = "Free"
  }
}

resource "azurerm_linux_web_app" "app" {
  name                = "suitedpockets"
  resource_group_name = azurerm_resource_group.rg.name
  location            = azurerm_resource_group.rg.location
  service_plan_id     = azurerm_app_service_plan.asp.id

  site_config {
    always_on = false  # Cannot be enabled on the Free tier
  }

  app_settings = {
    "WEBSITE_STACK"                  = "python"
    "PYTHON_VERSION"                 = "3.10"
    "SCM_DO_BUILD_DURING_DEPLOYMENT" = "true"
    "DB_SERVER"                      = azurerm_mssql_server.sql.fully_qualified_domain_name
  }

  https_only = true
}

resource "random_password" "pass" {
  length  = 24
  special = true
}

resource "azurerm_mssql_server" "sql" {
  name                          = var.db_name
  resource_group_name           = azurerm_resource_group.rg.name
  location                      = azurerm_resource_group.rg.location
  administrator_login           = "sqladmin"
  administrator_login_password  = random_password.pass.result
  version                       = "12.0"
  public_network_access_enabled = true

  azuread_administrator {
    object_id      = data.azurerm_client_config.current.object_id
    login_username = data.azuread_user.current_user.user_principal_name
  }

}

resource "azurerm_sql_database" "db" {
  name                = "poker"
  resource_group_name = azurerm_resource_group.rg.name
  location            = azurerm_resource_group.rg.location
  server_name         = azurerm_mssql_server.sql.name
  requested_service_objective_name = "GP_S_Gen5_1"

  # Enable serverless tier
  elastic_pool_name = null
  max_size_gb       = 5  # Free tier limit, adjust as needed

}

output "sql_password" {
  value     = random_password.pass.result
  sensitive = true
}