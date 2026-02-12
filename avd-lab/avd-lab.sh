#!/usr/bin/env bash
#
# AVD Lab Lifecycle Tool - Manage Azure Virtual Desktop lab environments
#
# A CLI tool to provision and tear down Azure Virtual Desktop (AVD) environments
# for course testing with minimal manual steps and clear cost controls.
#
# Exit codes:
#   0 - Success
#   1 - Validation/config error
#   2 - Azure API/deploy failure
#   3 - Safety check blocked action
#

set -euo pipefail

# ============== Configuration ==============
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
LOGS_DIR="${SCRIPT_DIR}/logs/avd-lab"
CONFIG_DIR="${SCRIPT_DIR}/config"
IAC_DIR="${SCRIPT_DIR}/iac"

# Exit codes
EXIT_SUCCESS=0
EXIT_VALIDATION_ERROR=1
EXIT_AZURE_ERROR=2
EXIT_SAFETY_BLOCKED=3

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
CYAN='\033[0;36m'
NC='\033[0m' # No Color

# ============== Logging Functions ==============
init_logging() {
    mkdir -p "$LOGS_DIR"
    LOG_FILE="${LOGS_DIR}/$(date +%Y%m%d-%H%M%S).log"
}

log() {
    local level="$1"
    local message="$2"
    local timestamp=$(date -u +"%Y-%m-%dT%H:%M:%S.fffZ")
    
    # JSON log
    echo "{\"timestamp\":\"$timestamp\",\"level\":\"$level\",\"message\":\"$message\"}" >> "$LOG_FILE"
    
    # Human-readable output
    local color="$CYAN"
    case "$level" in
        WARN) color="$YELLOW" ;;
        ERROR) color="$RED" ;;
        DEBUG) color='\033[0;90m' ;;
    esac
    echo -e "${color}[$level]${NC} $message"
}

log_success() {
    echo -e "${GREEN}✓${NC} $1"
}

log_error_exit() {
    local message="$1"
    local exit_code="${2:-$EXIT_VALIDATION_ERROR}"
    log "ERROR" "$message"
    exit "$exit_code"
}

# ============== Argument Parsing ==============
parse_arguments() {
    CONFIG=""
    NAME=""
    LAB_ID=""
    PARTICIPANT=""
    TTL=""
    HOURS=""
    SUBSCRIPTION=""
    RG_MODE="new_per_lab" # new_per_lab | existing
    RG_NAME=""
    EMAIL=""
    STUDENTS=""
    YES=false
    DRY_RUN=false
    
    while [[ $# -gt 0 ]]; do
        case "$1" in
            --config)
                CONFIG="$2"
                shift 2
                ;;
            --name)
                NAME="$2"
                shift 2
                ;;
            --lab-id)
                LAB_ID="$2"
                shift 2
                ;;
            --participant)
                PARTICIPANT="$2"
                shift 2
                ;;
            --ttl)
                TTL="$2"
                shift 2
                ;;
            --hours)
                HOURS="$2"
                shift 2
                ;;
            --subscription)
                SUBSCRIPTION="$2"
                shift 2
                ;;
            --email)
                EMAIL="$2"
                shift 2
                ;;
            --students)
                STUDENTS="$2"
                shift 2
                ;;
            --rg-mode)
                RG_MODE="$2"
                shift 2
                ;;
            --rg-name)
                RG_NAME="$2"
                shift 2
                ;;
            --yes|-y)
                YES=true
                shift
                ;;
            --dry-run)
                DRY_RUN=true
                shift
                ;;
            *)
                shift
                ;;
        esac
    done
    
    # --lab-id takes precedence over --name
    if [[ -n "$LAB_ID" ]]; then
        NAME="$LAB_ID"
    fi
}

# ============== Lab ID Generation ==============
generate_lab_id() {
    local course="$1"
    local participant="$2"
    local timestamp
    timestamp=$(date +%Y%m%d%H%M)
    local rand4
    rand4=$(head /dev/urandom | tr -dc 'a-z0-9' | head -c 4)
    echo "${course}-${participant}-${timestamp}-${rand4}"
}

# ============== Preflight Checks ==============
check_existing_labs() {
    local participant="$1"
    local subscription_id
    subscription_id=$(az account show --query id -o tsv)
    
    log "INFO" "Checking for existing labs for participant: $participant"
    
    # Check for existing resources with same participant tag that are not expired
    local existing_labs
    existing_labs=$(az resource list \
        --tag "participant=$participant" \
        --query "[?tags.'managed-by'=='avd-lab-tool']" \
        -o json 2>/dev/null || echo "[]")
    
    local active_labs
    active_labs=$(echo "$existing_labs" | jq -r '
        .[] | 
        select(.tags.expiry != null) |
        select((.tags.expiry | fromdateiso8601) > (now)) |
        .tags."lab-id"
    ' | sort -u)
    
    if [[ -n "$active_labs" ]]; then
        log "ERROR" "Active lab(s) already exist for participant '$participant':"
        echo "$active_labs" | while read -r lab_id; do
            echo "  - $lab_id"
        done
        log_error_exit "Destroy existing lab(s) first or use a different participant slug" $EXIT_SAFETY_BLOCKED
    fi
    
    log_success "No active labs found for participant: $participant"
}

check_lab_id_exists() {
    local lab_id="$1"
    
    log "INFO" "Checking if lab-id '$lab_id' already exists..."
    
    local existing
    existing=$(az resource list \
        --tag "lab-id=$lab_id" \
        --query "length(@)" \
        -o tsv 2>/dev/null || echo "0")
    
    if [[ "$existing" -gt 0 ]]; then
        log_error_exit "Lab with id '$lab_id' already exists. This should not happen - please report." $EXIT_SAFETY_BLOCKED
    fi
    
    log_success "Lab-id '$lab_id' is available"
}

# ============== Configuration Loading ==============
load_config() {
    local config_path="$1"
    
    if [[ -z "$config_path" ]]; then
        log_error_exit "Configuration file path is required. Use --config <path>"
    fi
    
    local full_path
    if [[ "$config_path" = /* ]]; then
        full_path="$config_path"
    else
        full_path="${SCRIPT_DIR}/${config_path}"
    fi
    
    if [[ ! -f "$full_path" ]]; then
        log_error_exit "Configuration file not found: $full_path"
    fi
    
    # Read config and expand environment variables
    local config_content
    config_content=$(cat "$full_path")
    
    # Expand environment variables with ${VAR:-default} syntax
    # Use perl for reliable replacement
    if command -v perl &> /dev/null; then
        config_content=$(echo "$config_content" | perl -pe 's/\$\{([A-Za-z_][A-Za-z0-9_]*)(?::-(.*?))?\}/$ENV{$1} \/\/ $2/ge')
    else
        # Fallback: simple sed-based expansion for common patterns
        while [[ "$config_content" =~ \$\{([A-Za-z_][A-Za-z0-9_]*)(:-(.*?))?\} ]]; do
            local full_match="${BASH_REMATCH[0]}"
            local var_name="${BASH_REMATCH[1]}"
            local default_val="${BASH_REMATCH[3]:-}"
            local env_val="${!var_name:-$default_val}"
            config_content="${config_content//"$full_match"/$env_val}"
        done
    fi
    
    echo "$config_content"
}

# ============== Azure Prerequisites Check ==============
check_azure_prerequisites() {
    log "INFO" "Checking Azure prerequisites..."
    
    # Check Azure CLI
    if ! command -v az &> /dev/null; then
        log_error_exit "Azure CLI not found. Please install: https://docs.microsoft.com/cli/azure/install-azure-cli"
    fi
    log_success "Azure CLI found"
    
    # Check if logged in
    local account
    if ! account=$(az account show 2>/dev/null); then
        log_error_exit "Not logged in to Azure. Run: az login"
    fi
    
    local user_name
    user_name=$(echo "$account" | jq -r '.user.name')
    log_success "Logged in as: $user_name"
    
    local subscription_id
    local subscription_name
    
    # Switch subscription if requested
    if [[ -n "$SUBSCRIPTION" ]]; then
        log "INFO" "Switching context to subscription: $SUBSCRIPTION"
        if ! az account set --subscription "$SUBSCRIPTION"; then
             log_error_exit "Failed to set subscription context to '$SUBSCRIPTION'. Check permissions." $EXIT_AZURE_ERROR
        fi
    fi
    
    account=$(az account show)
    subscription_id=$(echo "$account" | jq -r '.id')
    subscription_name=$(echo "$account" | jq -r '.name')
    log_success "Subscription: $subscription_id ($subscription_name)"
    
    # Check required providers
    local providers=("Microsoft.DesktopVirtualization" "Microsoft.Compute" "Microsoft.Network" "Microsoft.Resources" "Microsoft.Storage")
    
    for provider in "${providers[@]}"; do
        local state
        state=$(az provider show --namespace "$provider" --query "registrationState" -o tsv 2>/dev/null || echo "NotRegistered")
        if [[ "$state" != "Registered" ]]; then
            log "WARN" "Registering provider: $provider"
            az provider register --namespace "$provider"
        fi
        log_success "Provider registered: $provider"
    done
    
    # Check Bicep
    local bicep_version
    if ! bicep_version=$(az bicep version 2>/dev/null); then
        log "WARN" "Installing Bicep..."
        az bicep install
        bicep_version=$(az bicep version)
    fi
    log_success "Bicep available: $bicep_version"
}

check_quota_availability() {
    local location="$1"
    local vm_size="$2"
    local count="$3"
    
    log "INFO" "Checking quota for $vm_size in $location..."
    
    local usage
    usage=$(az vm list-usage --location "$location" --query "[?name.value=='$vm_size']" -o json 2>/dev/null || echo "[]")

    # Some subscriptions/regions don't return per-size entries here.
    # In that case, warn and continue instead of hard-failing validate.
    local available
    available=$(echo "$usage" | jq -r 'if length == 0 or .[0] == null then "unknown" else ((.[0].limit // 0) - (.[0].currentValue // 0) | tostring) end')

    if [[ "$available" == "unknown" ]]; then
        log "WARN" "Could not determine quota for $vm_size in $location from az vm list-usage; skipping strict quota check."
        return 0
    fi
    
    if [[ "$available" -lt "$count" ]]; then
        log_error_exit "Insufficient quota for $vm_size in $location. Available: $available, Required: $count"
    fi
    log_success "Quota available: $available VMs of type $vm_size"
}

check_network_collision() {
    local address_prefix="$1"
    local location="$2"
    
    log "INFO" "Checking for network collisions with $address_prefix..."
    
    local vnets
    vnets=$(az network vnet list --query "[?location=='$location']" -o json 2>/dev/null)
    
    local collision
    collision=$(echo "$vnets" | jq -r ".[] | select(.addressSpace.addressPrefixes[] == \"$address_prefix\") | .name" | head -1)
    
    if [[ -n "$collision" ]]; then
        log_error_exit "Network collision detected: $address_prefix is already used by $collision"
    fi
    
    log_success "No network collisions detected"
}

# ============== Validate Command ==============
cmd_validate() {
    log "INFO" "Starting validation..."
    
    local config_json
    config_json=$(load_config "$CONFIG")
    
    check_azure_prerequisites
    
    local location
    local vm_size
    local vm_count
    local vnet_prefix
    
    location=$(echo "$config_json" | jq -r '.parameters.location.value')
    vm_size=$(echo "$config_json" | jq -r '.parameters.vmSize.value')
    vm_count=$(echo "$config_json" | jq -r '.parameters.numberOfSessionHosts.value')
    vnet_prefix=$(echo "$config_json" | jq -r '.parameters.vnetAddressPrefix.value')
    
    # Expand env vars in values
    location=$(eval echo "$location")
    
    check_quota_availability "$location" "$vm_size" "$vm_count"
    check_network_collision "$vnet_prefix" "$location"
    
    log "INFO" "Validation completed successfully"
    log_success "All prerequisites validated"
    
    return $EXIT_SUCCESS
}

# ============== Create Command ==============
# ============== Student Management ==============
cmd_invite_student() {
    if [[ -z "$EMAIL" ]]; then
        log_error_exit "Student email is required. Use --email <email>"
    fi
    
    log "INFO" "Inviting student: $EMAIL"
    

    local invite_output
    # Use Microsoft Graph API to create guest invitation
    if ! invite_output=$(az rest --method POST \
        --uri "https://graph.microsoft.com/v1.0/invitations" \
        --body "{\"invitedUserEmailAddress\": \"$EMAIL\", \"inviteRedirectUrl\": \"https://myapps.microsoft.com\"}" \
        -o json 2>&1); then
        log_error_exit "Failed to invite student: $invite_output" $EXIT_AZURE_ERROR
    fi
    
    local object_id
    object_id=$(echo "$invite_output" | jq -r '.invitedUser.id // empty')
    
    if [[ -z "$object_id" ]]; then
        # Fallback for some CLI versions
        object_id=$(echo "$invite_output" | jq -r '.id // empty')
    fi
    
    if [[ -z "$object_id" ]]; then
        log_error_exit "Failed to extract Object ID from invitation output: $invite_output" $EXIT_AZURE_ERROR
    fi
    
    log_success "Invited student $EMAIL (Object ID: $object_id)"
    
    # Return JSON for the TUI to parse
    echo "$invite_output"
    
    return $EXIT_SUCCESS
}

cmd_create() {
    log "INFO" "Starting AVD lab creation..."
    
    # Require participant slug
    if [[ -z "$PARTICIPANT" ]]; then
        log_error_exit "Participant slug is required. Use --participant <slug>"
    fi
    
    # Validate participant slug format (lowercase alphanumeric and hyphens only)
    if [[ ! "$PARTICIPANT" =~ ^[a-z0-9-]+$ ]]; then
        log_error_exit "Participant slug must be lowercase alphanumeric with hyphens only"
    fi
    if [[ ${#PARTICIPANT} -gt 20 ]]; then
        log_error_exit "Participant slug too long (max 20 chars) to keep Azure resource names valid"
    fi
    
    local config_json
    config_json=$(load_config "$CONFIG")
    
    check_azure_prerequisites
    
    # Get course name from config
    local course
    course=$(echo "$config_json" | jq -r '.parameters.tags.value.course // "azure"')
    course=$(eval echo "$course")
    # Sanitize course name for lab-id
    course=$(echo "$course" | tr '[:upper:]' '[:lower:]' | tr -cd 'a-z0-9-')
    
    # Generate unique lab-id
    local lab_id
    lab_id=$(generate_lab_id "$course" "$PARTICIPANT")
    
    log "INFO" "Generated lab-id: $lab_id"
    
    # Determine Resource Group Strategy
    local final_rg_name
    
    if [[ "$RG_MODE" == "existing" ]]; then
        if [[ -z "$RG_NAME" ]]; then
            log_error_exit "RG name is required when --rg-mode existing is used"
        fi
        
        # Verify existing RG
        log "INFO" "Verifying existing resource group: $RG_NAME"
        if ! az group show --name "$RG_NAME" &>/dev/null; then
             log_error_exit "Resource group '$RG_NAME' not found in current subscription"
        fi
        final_rg_name="$RG_NAME"
        log_success "Using existing resource group: $final_rg_name"
        
    else
        # New Per Lab Mode
        # In new mode, we typically use the lab_id as the RG name for isolation
        final_rg_name="$lab_id"
        log "INFO" "Will create new resource group: $final_rg_name"
    fi
    
    # Preflight checks
    check_existing_labs "$PARTICIPANT"
    check_lab_id_exists "$lab_id"
    
    # Calculate expiry time
    local ttl="${TTL:-8h}"
    local ttl_value
    local ttl_unit
    local expiry
    
    if [[ "$ttl" =~ ^([0-9]+)(h|d)$ ]]; then
        ttl_value="${BASH_REMATCH[1]}"
        ttl_unit="${BASH_REMATCH[2]}"
        
        if [[ "$ttl_unit" == "h" ]]; then
            expiry=$(date -u -d "+${ttl_value} hours" +"%Y-%m-%dT%H:%M:%SZ" 2>/dev/null || date -u -v+${ttl_value}H +"%Y-%m-%dT%H:%M:%SZ")
        else
            expiry=$(date -u -d "+${ttl_value} days" +"%Y-%m-%dT%H:%M:%SZ" 2>/dev/null || date -u -v+${ttl_value}d +"%Y-%m-%dT%H:%M:%SZ")
        fi
    else
        log_error_exit "Invalid TTL format. Use format like '8h' or '1d'"
    fi
    
    log "INFO" "Lab will expire at: $expiry"
    
    # Extract config values
    local location
    location=$(echo "$config_json" | jq -r '.parameters.location.value')
    location=$(eval echo "$location")
    
    local vm_size
    vm_size=$(echo "$config_json" | jq -r '.parameters.vmSize.value')
    
    local vm_image
    vm_image=$(echo "$config_json" | jq -r '.parameters.vmImage.value')
    
    local host_pool_type
    host_pool_type=$(echo "$config_json" | jq -r '.parameters.hostPoolType.value')
    
    local load_balancer_type
    load_balancer_type=$(echo "$config_json" | jq -r '.parameters.loadBalancerType.value')
    
    local max_sessions
    max_sessions=$(echo "$config_json" | jq -r '.parameters.maxSessionsPerHost.value')
    
    local num_hosts
    num_hosts=$(echo "$config_json" | jq -r '.parameters.numberOfSessionHosts.value')
    
    local vnet_prefix
    vnet_prefix=$(echo "$config_json" | jq -r '.parameters.vnetAddressPrefix.value')
    
    local subnet_prefix
    subnet_prefix=$(echo "$config_json" | jq -r '.parameters.subnetAddressPrefix.value')
    
    local aad_join_type
    aad_join_type=$(echo "$config_json" | jq -r '.parameters.aadJoinType.value')
    
    local owner
    owner=$(echo "$config_json" | jq -r '.parameters.tags.value.owner // "lab-admin"')
    owner=$(eval echo "$owner")
    
    local cost_center
    cost_center=$(echo "$config_json" | jq -r '.parameters.tags.value.costCenter // "training"')
    cost_center=$(eval echo "$cost_center")
    
    # Generate admin password
    local admin_password
    admin_password=$(openssl rand -base64 16 | tr -d '/+=' | head -c 16)A1!
    
    # Build tags with lab-id and participant
    local tags_json
    tags_json=$(cat <<EOF
{
    "managed-by": "avd-lab-tool",
    "lab-id": "$lab_id",
    "participant": "$PARTICIPANT",
    "course": "$course",
    "owner": "$owner",
    "costCenter": "$cost_center",
    "expiry": "$expiry"
}
EOF
)
    
    # Build parameters - use lab_id as resource group name and naming prefix
    # Note: resourceGroupName param in main.bicep might dictate creation or usage.
    # If RG_MODE is existing, we want main.bicep to deploy INTO it.
    
    local params_file="${SCRIPT_DIR}/temp-params.json"
    
    # Build student Object IDs array if provided
    local student_ids_json="[]"
    if [[ -n "$STUDENTS" ]]; then
        student_ids_json=$(echo "$STUDENTS" | sed 's/,/","/g' | sed 's/^/["/' | sed 's/$/"]/')
    fi

    cat > "$params_file" << EOF
{
    "resourceGroupName": {
        "value": "$final_rg_name"
    },
    "location": {
        "value": "$location"
    },
    "namingPrefix": {
        "value": "avd"
    },
    "namingSuffix": {
        "value": "$PARTICIPANT"
    },
    "vmSize": {
        "value": "$vm_size"
    },
    "vmImage": {
        "value": $vm_image
    },
    "hostPoolType": {
        "value": "$host_pool_type"
    },
    "loadBalancerType": {
        "value": "$load_balancer_type"
    },
    "maxSessionsPerHost": {
        "value": $max_sessions
    },
    "numberOfSessionHosts": {
        "value": $num_hosts
    },
    "vnetAddressPrefix": {
        "value": "$vnet_prefix"
    },
    "subnetAddressPrefix": {
        "value": "$subnet_prefix"
    },
    "aadJoinType": {
        "value": "$aad_join_type"
    },
    "adminPassword": {
        "value": "$admin_password"
    },
    "tags": {
        "value": $tags_json
    },
    "expiry": {
        "value": "$expiry"
    },
    "studentObjectIds": {
        "value": $student_ids_json
    }
}
EOF
    
    if [[ "$DRY_RUN" == true ]]; then
        log "INFO" "Dry run mode - would deploy with parameters:"
        cat "$params_file"
        rm -f "$params_file"
        return $EXIT_SUCCESS
    fi
    
    # Deploy
    log "INFO" "Deploying AVD lab: $lab_id"
    
    local bicep_file="${IAC_DIR}/main.bicep"
    local deployment_name="avd-lab-${lab_id}"
    
    local deployment_output
    if ! deployment_output=$(az deployment sub create \
        --location "$location" \
        --template-file "$bicep_file" \
        --parameters "@$params_file" \
        --name "$deployment_name" \
        -o json 2>&1); then
        rm -f "$params_file"
        log_error_exit "Deployment failed: $deployment_output" $EXIT_AZURE_ERROR
    fi
    
    rm -f "$params_file"
    
    # Parse outputs
    local rg_name
    local host_pool_name
    local workspace_name
    local workspace_url
    
    rg_name=$(echo "$deployment_output" | jq -r '.properties.outputs.resourceGroupName.value')
    host_pool_name=$(echo "$deployment_output" | jq -r '.properties.outputs.hostPoolName.value')
    workspace_name=$(echo "$deployment_output" | jq -r '.properties.outputs.workspaceName.value')
    workspace_url=$(echo "$deployment_output" | jq -r '.properties.outputs.workspaceUrl.value')
    local expiry_out
    expiry_out=$(echo "$deployment_output" | jq -r '.properties.outputs.expiry.value')
    
    # Output results
    log_success "AVD Lab created successfully!"
    echo ""
    echo "Lab ID: $lab_id"
    echo "Participant: $PARTICIPANT"
    echo "Resource Group: $rg_name"
    echo "Host Pool: $host_pool_name"
    echo "Workspace: $workspace_name"
    echo "Workspace URL: $workspace_url"
    echo "Expiry: $expiry_out"
    echo ""
    echo -e "${YELLOW}To destroy this lab, run:${NC}"
    echo "  ./avd-lab.sh destroy --lab-id $lab_id --yes"
    
    # Estimate cost
    local estimated_cost
    estimated_cost=$(estimate_cost "$config_json" "$ttl_value")
    echo ""
    echo -e "${CYAN}Estimated cost for TTL period: \$$estimated_cost${NC}"
    
    return $EXIT_SUCCESS
}

# ============== Destroy Command ==============
cmd_destroy() {
    log "INFO" "Starting AVD lab destruction..."
    
    # Require either --lab-id or --participant
    local lab_id=""
    local participant=""
    
    if [[ -n "$NAME" ]]; then
        # --name is now --lab-id for backward compatibility
        lab_id="$NAME"
    fi
    
    if [[ -n "$PARTICIPANT" ]]; then
        participant="$PARTICIPANT"
    fi
    
    if [[ -z "$lab_id" && -z "$participant" ]]; then
        log_error_exit "Lab ID or participant is required. Use --lab-id <id> or --participant <slug>"
    fi
    
    check_azure_prerequisites
    
    local rg_name
    
    if [[ -n "$lab_id" ]]; then
        # Find by lab-id tag
        log "INFO" "Looking up lab by lab-id: $lab_id"
        
        local lab_resources
        lab_resources=$(az resource list --tag "lab-id=$lab_id" --tag "managed-by=avd-lab-tool" -o json 2>/dev/null)
        
        if [[ $(echo "$lab_resources" | jq 'length') -eq 0 ]]; then
            # Try as resource group name for backward compatibility
            if az group show --name "$lab_id" &>/dev/null; then
                rg_name="$lab_id"
            else
                log_error_exit "No resources found with lab-id='$lab_id'"
            fi
        else
            # Get resource group from first resource
            rg_name=$(echo "$lab_resources" | jq -r '.[0].resourceGroup')
        fi
    else
        # Find by participant (only if single active lab)
        log "INFO" "Looking up lab by participant: $participant"
        
        local lab_resources
        lab_resources=$(az resource list --tag "participant=$participant" --tag "managed-by=avd-lab-tool" -o json 2>/dev/null)
        
        if [[ $(echo "$lab_resources" | jq 'length') -eq 0 ]]; then
            log_error_exit "No resources found with participant='$participant'"
        fi
        
        # Get unique lab-ids
        local lab_ids
        lab_ids=$(echo "$lab_resources" | jq -r '.[].tags."lab-id"' | sort -u)
        local lab_count
        lab_count=$(echo "$lab_ids" | wc -l)
        
        if [[ $lab_count -gt 1 ]]; then
            log "ERROR" "Multiple labs found for participant '$participant':"
            echo "$lab_ids" | while read -r id; do
                echo "  - $id"
            done
            log_error_exit "Specify --lab-id to target a specific lab" $EXIT_SAFETY_BLOCKED
        fi
        
        lab_id=$(echo "$lab_ids" | head -1)
        rg_name=$(echo "$lab_resources" | jq -r '.[0].resourceGroup')
    fi
    
    # Verify it's managed by this tool
    local rg
    rg=$(az group show --name "$rg_name" 2>/dev/null)
    if [[ -z "$rg" ]]; then
        log_error_exit "Resource group '$rg_name' not found"
    fi
    
    local managed_by
    managed_by=$(echo "$rg" | jq -r '.tags."managed-by" // empty')
    if [[ "$managed_by" != "avd-lab-tool" ]]; then
        log_error_exit "Resource group '$rg_name' is not managed by avd-lab-tool. Refusing to delete for safety." $EXIT_SAFETY_BLOCKED
    fi
    
    # Get lab-id from RG if not set
    if [[ -z "$lab_id" ]]; then
        lab_id=$(echo "$rg" | jq -r '.tags."lab-id" // empty')
    fi
    
    # Show delete plan
    echo ""
    echo -e "${YELLOW}Resources to be deleted:${NC}"
    echo "  Lab ID: $lab_id"
    echo "  Resource Group: $rg_name"
    
    local resources
    resources=$(az resource list --resource-group "$rg_name" -o json 2>/dev/null)
    echo "$resources" | jq -r '.[] | "  - \(.type): \(.name)"'
    echo ""
    
    # Confirm deletion
    if [[ "$YES" != true ]]; then
        read -p "Are you sure you want to delete these resources? (yes/no): " confirm
        if [[ "$confirm" != "yes" ]]; then
            log "INFO" "Deletion cancelled by user"
            return $EXIT_SUCCESS
        fi
    fi
    
    # Delete resource group
    log "INFO" "Deleting resource group: $rg_name"
    
    az group delete --name "$rg_name" --yes --no-wait
    
    if [[ $? -ne 0 ]]; then
        log_error_exit "Failed to delete resource group" $EXIT_AZURE_ERROR
    fi
    
    # Poll for completion
    log "INFO" "Deletion in progress..."
    local max_wait=300
    local waited=0
    
    while [[ $waited -lt $max_wait ]]; do
        if ! az group show --name "$rg_name" &>/dev/null; then
            break
        fi
        sleep 10
        ((waited += 10))
        echo -n "."
    done
    echo ""
    
    # Scan for orphaned resources
    log "INFO" "Scanning for orphaned resources..."
    local orphaned
    orphaned=$(az resource list --tag "lab-id=$lab_id" -o json 2>/dev/null)
    
    if [[ $(echo "$orphaned" | jq 'length') -gt 0 ]]; then
        log "WARN" "Found $(echo "$orphaned" | jq 'length') orphaned resources:"
        echo "$orphaned" | jq -r '.[] | "  - \(.type): \(.name)"'
    else
        log_success "No orphaned resources found"
    fi
    
    log_success "AVD Lab destroyed successfully"
    
    return $EXIT_SUCCESS
}

# ============== Status Command ==============
cmd_status() {
    log "INFO" "Getting AVD lab status..."
    
    # Require either --lab-id or --participant
    local lab_id=""
    local participant=""
    
    if [[ -n "$NAME" ]]; then
        lab_id="$NAME"
    fi
    
    if [[ -n "$PARTICIPANT" ]]; then
        participant="$PARTICIPANT"
    fi
    
    if [[ -z "$lab_id" && -z "$participant" ]]; then
        log_error_exit "Lab ID or participant is required. Use --lab-id <id> or --participant <slug>"
    fi
    
    check_azure_prerequisites
    
    local rg_name
    
    if [[ -n "$lab_id" ]]; then
        # Find by lab-id tag
        local lab_resources
        lab_resources=$(az resource list --tag "lab-id=$lab_id" --tag "managed-by=avd-lab-tool" -o json 2>/dev/null)
        
        if [[ $(echo "$lab_resources" | jq 'length') -eq 0 ]]; then
            # Try as resource group name for backward compatibility
            if az group show --name "$lab_id" &>/dev/null; then
                rg_name="$lab_id"
            else
                log_error_exit "Lab '$lab_id' not found"
            fi
        else
            rg_name=$(echo "$lab_resources" | jq -r '.[0].resourceGroup')
        fi
    else
        # Find by participant
        local lab_resources
        lab_resources=$(az resource list --tag "participant=$participant" --tag "managed-by=avd-lab-tool" -o json 2>/dev/null)
        
        if [[ $(echo "$lab_resources" | jq 'length') -eq 0 ]]; then
            log_error_exit "No lab found for participant '$participant'"
        fi
        
        # Get unique lab-ids
        local lab_ids
        lab_ids=$(echo "$lab_resources" | jq -r '.[].tags."lab-id"' | sort -u)
        local lab_count
        lab_count=$(echo "$lab_ids" | wc -l)
        
        if [[ $lab_count -gt 1 ]]; then
            log "WARN" "Multiple labs found for participant '$participant':"
            echo "$lab_ids" | while read -r id; do
                echo "  - $id"
            done
            log_error_exit "Specify --lab-id to view a specific lab" $EXIT_SAFETY_BLOCKED
        fi
        
        lab_id=$(echo "$lab_ids" | head -1)
        rg_name=$(echo "$lab_resources" | jq -r '.[0].resourceGroup')
    fi
    
    # Check resource group
    local rg
    if ! rg=$(az group show --name "$rg_name" 2>/dev/null); then
        log_error_exit "Lab '$lab_id' not found"
    fi
    
    local rg_location
    rg_location=$(echo "$rg" | jq -r '.location')
    local rg_tags
    rg_tags=$(echo "$rg" | jq -r '.tags')
    
    # Get lab-id from RG if not set
    if [[ -z "$lab_id" ]]; then
        lab_id=$(echo "$rg_tags" | jq -r '."lab-id" // empty')
    fi
    
    echo ""
    echo -e "${CYAN}AVD Lab Status${NC}"
    echo "================================"
    echo "Lab ID: $lab_id"
    echo "Resource Group: $rg_name"
    echo "Location: $rg_location"
    echo "Tags:"
    echo "$rg_tags" | jq -r 'to_entries[] | "  \(.key): \(.value)"'
    
    # Get host pools
    local host_pools
    host_pools=$(az desktopvirtualization host-pool list --resource-group "$rg_name" -o json 2>/dev/null || echo "[]")
    
    if [[ $(echo "$host_pools" | jq 'length') -gt 0 ]]; then
        echo ""
        echo -e "${CYAN}Host Pools:${NC}"
        echo "$host_pools" | jq -r '.[] | "  Name: \(.name)\n  Type: \(.properties.hostPoolType)\n  Max Sessions: \(.properties.maxSessionLimit)"'
    fi
    
    # Get session hosts
    if [[ $(echo "$host_pools" | jq 'length') -gt 0 ]]; then
        echo ""
        echo -e "${CYAN}Session Hosts:${NC}"
        for hp_name in $(echo "$host_pools" | jq -r '.[].name'); do
            local session_hosts
            session_hosts=$(az desktopvirtualization session-host list --resource-group "$rg_name" --host-pool-name "$hp_name" -o json 2>/dev/null || echo "[]")
            echo "$session_hosts" | jq -r '.[] | "  \(.name): \(.properties.status)"'
        done
    fi
    
    # Get VMs
    local vms
    vms=$(az vm list --resource-group "$rg_name" -o json 2>/dev/null || echo "[]")
    
    if [[ $(echo "$vms" | jq 'length') -gt 0 ]]; then
        echo ""
        echo -e "${CYAN}Virtual Machines:${NC}"
        for vm_name in $(echo "$vms" | jq -r '.[].name'); do
            local power_state
            power_state=$(az vm get-instance-view --name "$vm_name" --resource-group "$rg_name" --query "instanceView.statuses[?code=='PowerState/running']" -o tsv 2>/dev/null || echo "")
            if [[ -n "$power_state" ]]; then
                echo -e "  $vm_name: ${GREEN}Running${NC}"
            else
                echo -e "  $vm_name: ${YELLOW}Stopped${NC}"
            fi
        done
    fi
    
    # Check expiry
    local expiry
    expiry=$(echo "$rg_tags" | jq -r '.expiry // empty')
    if [[ -n "$expiry" ]]; then
        local expiry_epoch
        local now_epoch
        
        if date -d "$expiry" &>/dev/null; then
            expiry_epoch=$(date -d "$expiry" +%s)
        else
            expiry_epoch=$(date -j -f "%Y-%m-%dT%H:%M:%SZ" "$expiry" +%s 2>/dev/null || echo "0")
        fi
        now_epoch=$(date +%s)
        
        if [[ "$expiry_epoch" -lt "$now_epoch" ]]; then
            echo ""
            echo -e "${RED}⚠ Lab has expired! Consider destroying it.${NC}"
        else
            local remaining=$((expiry_epoch - now_epoch))
            local days=$((remaining / 86400))
            local hours=$(((remaining % 86400) / 3600))
            local minutes=$(((remaining % 3600) / 60))
            echo ""
            echo -e "${CYAN}Time remaining: ${days}d ${hours}h ${minutes}m${NC}"
        fi
    fi
    
    return $EXIT_SUCCESS
}

# ============== Estimate Cost Command ==============
estimate_cost() {
    local config_json="$1"
    local hours="${2:-8}"
    
    # Rough cost estimates (USD/hour)
    declare -A vm_costs
    vm_costs["Standard_D2s_v3"]=0.10
    vm_costs["Standard_D4s_v3"]=0.20
    vm_costs["Standard_D8s_v3"]=0.40
    vm_costs["Standard_D2s_v4"]=0.11
    vm_costs["Standard_D4s_v4"]=0.22
    vm_costs["Standard_D8s_v4"]=0.44
    vm_costs["Standard_D2s_v5"]=0.12
    vm_costs["Standard_D4s_v5"]=0.24
    vm_costs["Standard_D8s_v5"]=0.48
    
    local vm_size
    vm_size=$(echo "$config_json" | jq -r '.parameters.vmSize.value')
    local vm_count
    vm_count=$(echo "$config_json" | jq -r '.parameters.numberOfSessionHosts.value')
    
    local hourly_rate="${vm_costs[$vm_size]:-0.15}"
    
    # Add storage cost (approx $0.10/GB/month for Premium SSD)
    # Use awk for floating point math (more portable than bc)
    local storage_cost
    storage_cost=$(awk "BEGIN {printf \"%.4f\", 127 * 0.10 / 730 * $vm_count}")
    
    # Add network cost (approx $0.01/hour)
    local network_cost=0.01
    
    local total_hourly
    total_hourly=$(awk "BEGIN {printf \"%.4f\", ($hourly_rate * $vm_count) + $storage_cost + $network_cost}")
    
    local total_cost
    total_cost=$(awk "BEGIN {printf \"%.2f\", $total_hourly * $hours}")
    
    echo "$total_cost"
}

cmd_estimate_cost() {
    log "INFO" "Estimating AVD lab cost..."
    
    local config_json
    config_json=$(load_config "$CONFIG")
    
    local hours="${HOURS:-8}"
    local cost
    cost=$(estimate_cost "$config_json" "$hours")
    
    local vm_size
    vm_size=$(echo "$config_json" | jq -r '.parameters.vmSize.value')
    local vm_count
    vm_count=$(echo "$config_json" | jq -r '.parameters.numberOfSessionHosts.value')
    
    echo ""
    echo -e "${CYAN}Cost Estimate${NC}"
    echo "============="
    echo "VM Size: $vm_size"
    echo "Number of VMs: $vm_count"
    echo "Duration: $hours hours"
    echo ""
    echo -e "${GREEN}Estimated Total Cost: \$$cost USD${NC}"
    echo ""
    echo -e "${YELLOW}Note: This is a rough estimate. Actual costs may vary based on:${NC}"
    echo "  - Region pricing differences"
    echo "  - Data transfer costs"
    echo "  - Actual usage patterns"
    
    return $EXIT_SUCCESS
}

# ============== Help ==============
show_help() {
    cat << 'EOF'
AVD Lab Lifecycle Tool - Manage Azure Virtual Desktop lab environments

USAGE:
    ./avd-lab.sh <command> [options]

COMMANDS:
    validate        Validate prerequisites and configuration
    create          Create a new AVD lab environment
    destroy         Destroy an AVD lab environment
    status          Show status of an AVD lab environment
    estimate-cost   Estimate cost for running a lab
    help            Show this help message

OPTIONS:
    --config <path>       Path to configuration file (required for validate, create, estimate-cost)
    --participant <slug>  Participant slug (required for create; can be used for destroy/status)
    --name <lab-id>       Lab ID (for destroy/status; can also use --lab-id)
    --lab-id <id>         Lab ID (for destroy/status)
    --ttl <duration>      Time-to-live for the lab (e.g., '8h', '1d')
    --hours <number>      Hours for cost estimation
    --yes                 Skip confirmation prompts
    --dry-run             Show what would be done without making changes

LAB ID FORMAT:
    Lab IDs are auto-generated as: <course>-<participant>-<YYYYMMDDHHmm>-<rand4>
    Example: azure-lenny-202602120938-a7k2

EXAMPLES:
    # Validate prerequisites
    ./avd-lab.sh validate --config config/lab-dev.json

    # Create a lab with participant slug (generates unique lab-id)
    ./avd-lab.sh create --config config/lab-dev.json --participant lenny --ttl 8h

    # Check lab status by participant
    ./avd-lab.sh status --participant lenny

    # Check lab status by lab-id
    ./avd-lab.sh status --lab-id azure-lenny-202602120938-a7k2

    # Estimate cost for 8 hours
    ./avd-lab.sh estimate-cost --config config/lab-dev.json --hours 8

    # Destroy a lab by participant
    ./avd-lab.sh destroy --participant lenny --yes

    # Destroy a lab by lab-id
    ./avd-lab.sh destroy --lab-id azure-lenny-202602120938-a7k2 --yes

ENVIRONMENT VARIABLES:
    AZ_SUBSCRIPTION_ID   Azure subscription ID
    AZ_LOCATION          Azure region
    OWNER                Owner tag value
    COURSE               Course tag value (used in lab-id)
    COST_CENTER          Cost center tag value

EXIT CODES:
    0  Success
    1  Validation/config error
    2  Azure API/deploy failure
    3  Safety check blocked action

EOF
}

# ============== Main ==============
init_logging

COMMAND="${1:-help}"
shift || true

parse_arguments "$@"

case "$COMMAND" in
    validate)
        cmd_validate
        ;;
    create)
        cmd_create
        ;;
    destroy)
        cmd_destroy
        ;;
    status)
        cmd_status
        ;;
    estimate-cost)
        cmd_estimate_cost
        ;;
    invite-student)
        cmd_invite_student
        ;;
    help|--help|-h)
        show_help
        exit $EXIT_SUCCESS
        ;;
    *)
        echo "Unknown command: $COMMAND"
        show_help
        exit $EXIT_VALIDATION_ERROR
        ;;
esac
