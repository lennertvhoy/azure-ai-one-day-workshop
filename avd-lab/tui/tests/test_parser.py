import pytest
from services.parser import OutputParser

@pytest.fixture
def parser():
    return OutputParser()

def test_parse_create_success(parser):
    output = """
Lab ID: azure-test-20230101-1234
Participant: test-user
Resource Group: rg-test
Host Pool: hp-test
Workspace: ws-test
Workspace URL: https://example.com
Expiry: 2023-01-02T00:00:00Z
Estimated cost for TTL period: $1.23
./avd-lab.sh destroy --lab-id azure-test-20230101-1234 --yes
AVD Lab created successfully
    """
    result = parser.parse_create(output)
    assert result.success
    assert result.lab_id == "azure-test-20230101-1234"
    assert result.participant == "test-user"
    assert result.estimated_cost == "$1.23"
    assert "destroy --lab-id azure-test-20230101-1234" in result.destroy_command

def test_parse_create_failure(parser):
    output = """
[ERROR] Failed to create resource group
[ERROR] Deployment failed
    """
    result = parser.parse_create(output)
    assert not result.success
    assert len(result.errors) == 2
    assert "Failed to create resource group" in result.errors

def test_extract_lab_list(parser):
    # Mocking az resource list output
    output = """
[
  {
    "id": "/subscriptions/sub/resourceGroups/rg1/providers/Microsoft.Resources/deploymentScripts/ds1",
    "location": "eastus",
    "resourceGroup": "rg1",
    "tags": {
      "lab-id": "lab1",
      "managed-by": "avd-lab-tool",
      "participant": "user1",
      "expiry": "2024-01-01T12:00:00Z"
    }
  },
  {
    "id": "/subscriptions/sub/resourceGroups/rg2/providers/Microsoft.Resources/deploymentScripts/ds2",
    "location": "westus",
    "resourceGroup": "rg2",
    "tags": {
      "lab-id": "lab2",
      "managed-by": "avd-lab-tool",
      "participant": "user2",
      "expiry": "unknown"
    }
  }
]
    """
    labs = parser.extract_lab_list(output)
    assert len(labs) == 2
    assert labs[0].lab_id == "lab1"
    assert labs[0].participant == "user1"
    assert labs[1].lab_id == "lab2"
    assert labs[1].status == "unknown"

def test_parse_destroy_success(parser):
    output = """
Lab ID: lab1
Resource Group: rg1
Resources to be deleted:
  - vm1
  - nic1
AVD Lab destroyed successfully
    """
    result = parser.parse_destroy(output)
    assert result.success
    assert result.lab_id == "lab1"
    assert "vm1" in result.resources_deleted

def test_parse_validation_success(parser):
    output = """
Azure CLI found
Logged in as: user@example.com
Subscription: Sub Name (sub-id)
Provider registered: Microsoft.Compute
Bicep available: 1.0.0
Quota available: 10 VMs of type Standard_D2s_v3
No network collisions detected
All prerequisites validated
    """
    result = parser.parse_validation(output)
    assert result.success
    assert result.azure_cli
    assert result.logged_in
    assert result.quota_available
    assert result.network_ok
