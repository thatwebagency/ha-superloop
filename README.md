# Superloop Card
A HACS integration to view Superloop account usage.

## Installation

### HACS Installation
1. Open HACS in your Home Assistant instance
2. Go to "Integrations"
3. Click the three dots in the top right corner and select "Custom repositories"
4. Add the URL to this repository and select "Integration" as the category
5. Click "Add"
6. Search for "Superloop" in the integrations tab
7. Click "Install"
8. Restart Home Assistant

### Manual Installation
1. Copy the `custom_components/superloop` directory to your `custom_components` directory in your Home Assistant configuration directory
2. Restart Home Assistant

## Configuration
1. Go to Settings -> Devices & Services
2. Click "+ Add Integration"
3. Search for "Superloop"
4. Enter your Superloop email and password

## Features
This integration provides sensors for:
- Data Used
- Data Remaining
- Data Limit
- Days Remaining in Billing Cycle
- Plan Speed
- Billing Cycle Start Date
- Billing Cycle End Date

## Troubleshooting
If you encounter any issues:
1. Check the Home Assistant logs for error messages
2. Verify your Superloop credentials are correct
3. Open an issue on GitHub with the error details

## Support
For support, please open an issue on GitHub.

## Dashboard Setup
We recommend installing mini-graph-card via HACS for a beautiful Superloop usage graph!

Example:

type: custom:mini-graph-card
entities:
  - entity: sensor.superloop_total_usage
  - entity: sensor.superloop_billing_progress
name: Superloop Usage
line_width: 5
smoothing: true