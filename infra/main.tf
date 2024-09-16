data "azurerm_client_config" "current" {}

data "azuread_user" "current_user" {
  object_id = data.azurerm_client_config.current.object_id
}

resource "azuread_application" "app" {
  display_name = "Suited Pockets"
}

resource "azuread_service_principal" "sp" {
  application_id = azuread_application.app.application_id
}

resource "azurerm_resource_group" "rg" {
  name     = "poker-stats"
  location = var.region
}

resource "azurerm_app_service_plan" "asp" {
  name                = "service-plan"
  location            = azurerm_resource_group.rg.location
  resource_group_name = azurerm_resource_group.rg.name
  kind                = "Linux"
  reserved            = true

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

  app_settings = {
    "SCM_DO_BUILD_DURING_DEPLOYMENT" = "true"
    "WEBSITES_PORT"                  = "8000"
    "DB_SERVER"                      = azurerm_mssql_server.sql.fully_qualified_domain_name
  }

  site_config {
    application_stack {
      python_version = "3.10"
    }
    app_command_line = "shiny run app.py --port 8000"
    always_on        = false  # Cannot be enabled on the Free tier
  }

  https_only = true

  identity {
    type = "SystemAssigned"
  }
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

