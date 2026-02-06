#!/bin/bash
# Download all required BOTSv3 Splunk Add-ons
#
# IMPORTANT: Most Splunkbase downloads require authentication.
# This script documents all required add-ons and provides download links.
# You may need to manually download some add-ons from Splunkbase with your account.
#
# Usage: ./download_addons.sh [--check-only]

set -e

ADDONS_DIR="${1:-../resources/splunk-add-ons}"
mkdir -p "$ADDONS_DIR"
cd "$ADDONS_DIR"

echo "=============================================="
echo "BOTSv3 Required Splunk Add-ons Downloader"
echo "=============================================="
echo ""
echo "Target directory: $(pwd)"
echo ""

# Define all required add-ons from BOTSv3 README
# Format: "name|version|splunkbase_id|filename"
declare -a REQUIRED_ADDONS=(
    "Amazon GuardDuty Add-on for Splunk|1.0.4|3790|amazon-guardduty-add-on-for-splunk_104.tgz"
    "Cisco Endpoint Security Analytics (CESA/NVM)|1.0.346|2992|cisco-endpoint-security-analytics-cesa_408.tgz"
    "Code42 App For Splunk|3.0.6|3736|code42-app-for-splunk_306.tgz"
    "Code42ForSplunk Technology Add-On|3.0.4|3746|code42-ta-for-splunk_304.tgz"
    "Splunk Add-on for Cisco ASA|3.3.0|1620|splunk-add-on-for-cisco-asa_600.tgz"
    "Splunk Add-on for Microsoft Cloud Services|2.1.0|3110|splunk-add-on-for-microsoft-cloud-services_210.tgz"
    "Splunk Add-on for Microsoft Office 365|1.0.0|4055|splunk-add-on-for-microsoft-office-365_100.tgz"
    "Splunk Add-on for Microsoft Windows|4.8.4|742|splunk-add-on-for-microsoft-windows_912.tgz"
    "Splunk Add-on for Symantec Endpoint Protection|2.3.0|2772|splunk-add-on-for-symantec-endpoint-protection_400.tgz"
    "Splunk Add-on for Tenable|5.1.3|1710|splunk-add-on-for-tenable_513.tgz"
    "Splunk Add-on for Unix and Linux|5.2.4|833|splunk-add-on-for-unix-and-linux_524.tgz"
    "Splunk Common Information Model|4.11.0|1621|splunk-common-information-model_4110.tgz"
    "Splunk Security Essentials|2.2.0|3435|splunk-security-essentials_220.tgz"
    "Splunk Stream Add-on|7.1.2|1809|splunk-stream-add-on_712.tgz"
    "TA-VirusTotalActions|0.2.0|3446|ta-virustotalactions_020.tgz"
    "URL Toolbox|1.6|2734|url-toolbox_16.tgz"
    "DecryptCommands|2.0|2655|decryptcommands_20.tgz"
    "Microsoft Azure AD Reporting Add-on|1.0.1|3757|microsoft-azure-ad-reporting-add-on_101.tgz"
    "Microsoft Cloud App for Splunk|1.0.1|3786|microsoft-cloud-app-for-splunk_101.tgz"
    "Microsoft Office 365 Reporting Add-on|1.0.1|3720|microsoft-office-365-reporting-add-on_101.tgz"
    "Microsoft Sysmon Add-on|8.0.0|1914|splunk-add-on-for-microsoft-sysmon_1062.tgz"
    "OSquery App for Splunk|0.6.0|3902|osquery-app-for-splunk_060.tgz"
    "Splunk Add-on for AWS|4.5.0|1876|splunk-add-on-for-amazon-web-services-aws_810.tgz"
    "ES Content Updates|1.0.25|3449|es-content-updates_1025.tgz"
    "SA-cim_vladiator|1.2|2968|sa-cim-vladiator_12.tgz"
)

echo "Checking for existing add-ons..."
echo ""

MISSING_COUNT=0
FOUND_COUNT=0

for addon in "${REQUIRED_ADDONS[@]}"; do
    IFS='|' read -r name version splunkbase_id filename <<< "$addon"

    # Check if any version of this add-on exists (fuzzy match on base name)
    base_name=$(echo "$filename" | sed 's/_[0-9]*\.tgz$//')
    existing=$(ls -1 ${base_name}*.tgz 2>/dev/null | head -1 || true)

    if [ -n "$existing" ]; then
        echo "[FOUND] $name"
        echo "        File: $existing"
        ((FOUND_COUNT++))
    else
        echo "[MISSING] $name (v$version)"
        echo "          Splunkbase: https://splunkbase.splunk.com/app/$splunkbase_id/"
        echo "          Expected: $filename"
        ((MISSING_COUNT++))
    fi
done

echo ""
echo "=============================================="
echo "Summary: $FOUND_COUNT found, $MISSING_COUNT missing"
echo "=============================================="

if [ "$MISSING_COUNT" -gt 0 ]; then
    echo ""
    echo "To download missing add-ons:"
    echo "1. Visit each Splunkbase URL above"
    echo "2. Login with your Splunk account"
    echo "3. Download the add-on (.tgz file)"
    echo "4. Place it in: $(pwd)"
    echo ""
    echo "Alternatively, you can use Splunk's REST API with authentication:"
    echo "  curl -u 'username:password' -o addon.tgz 'https://splunkbase.splunk.com/app/XXXX/release/X.X.X/download/'"
    echo ""
    echo "Note: The exact versions from BOTSv3 may not be available."
    echo "      Newer versions usually work but may have different field extractions."
fi

# Check for the pre-bundled tarball
if [ -f "../splunk-add-ons-for-botsv3.tgz" ]; then
    echo ""
    echo "Found pre-bundled add-ons archive: ../splunk-add-ons-for-botsv3.tgz"
    echo "You can extract it with: tar -xzf ../splunk-add-ons-for-botsv3.tgz -C ."
fi

echo ""
echo "After downloading add-ons, rebuild the Docker image:"
echo "  cd scripts && docker build -t splunk-botsv3 ."
