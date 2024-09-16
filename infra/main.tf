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
  name                = "poker-app"
  resource_group_name = azurerm_resource_group.rg.name
  location            = azurerm_resource_group.rg.location
  service_plan_id     = azurerm_app_service_plan.asp.id

  site_config {
    always_on = false  # Cannot be enabled on the Free tier
  }
  app_settings = {
    "WEBSITE_STACK"       = "python"
    "PYTHON_VERSION"      = "3.10"
    "SCM_DO_BUILD_DURING_DEPLOYMENT" = "true"
  }

  https_only = true
}