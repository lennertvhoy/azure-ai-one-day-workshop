# Infra — Resource Setup (Trainer / Participants)

## Recommended region
- **westeurope** (Belgium-friendly)

## Naming convention (example)
- RG: `rg-aiws-<name>`
- KV: `kv-aiws-<name>`
- WebApp: `app-aiws-<name>`
- Search: `srch-aiws-<name>`

## Role assignments (minimum)
- Web App Managed Identity:
  - `Key Vault Secrets User` on Key Vault

## Notes on Azure OpenAI auth
- Many tenants still require **API key** for AOAI. We store it in Key Vault and reference from Web App.
- If your tenant supports Entra ID / managed identity for AOAI, you can upgrade later.

## Budget-friendly defaults
- App Service plan: `B1` for class
- AI Search: `basic`

## Az CLI quickstart
```bash
az login
az account show
az provider register --namespace Microsoft.CognitiveServices
az provider register --namespace Microsoft.Search
az provider register --namespace Microsoft.Web
az provider register --namespace Microsoft.KeyVault
```
