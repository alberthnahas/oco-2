#!/bin/bash

# === USER INPUT ===
YEAR=2025
MONTH=04  # Format must be 01 to 12
# ===================

# Base URL for accessing data
BASE_URL="https://oco2.gesdisc.eosdis.nasa.gov/data/OCO2_DATA/OCO2_L2_Standard.11.2/$YEAR"

# Output directory (flat)
OUTPUT_DIR="./"
mkdir -p "$OUTPUT_DIR"

# Start total timer
TOTAL_START=$(date +%s)

# Calculate number of days in the month
LAST_DAY=$(date -d "$YEAR-$MONTH-01 +1 month -1 day" +%d)

# Loop over each day in the month, convert to DOY
for DAY in $(seq -f "%02g" 1 "$LAST_DAY"); do
    DATE="$YEAR-$MONTH-$DAY"
    DOY=$(date -d "$DATE" +%j)

    DAY_URL="$BASE_URL/$DOY/"
    echo "-----------------------------"
    echo "Checking availability for $DAY_URL"

    if curl --head --silent --fail "$DAY_URL" > /dev/null; then
        echo "Downloading from $DAY_URL"
        START=$(date +%s)

        wget --load-cookies ~/.urs_cookies --save-cookies ~/.urs_cookies --keep-session-cookies \
             --content-disposition -r -nd -np -A "*.h5" \
             -P "$OUTPUT_DIR" \
             "$DAY_URL"

        END=$(date +%s)
        ELAPSED=$((END - START))
        echo "Finished downloading DOY $DOY in $ELAPSED seconds"
    else
        echo "DOY $DOY not available (404 Not Found). Skipping..."
    fi
done

# Show total time
TOTAL_END=$(date +%s)
TOTAL_ELAPSED=$((TOTAL_END - TOTAL_START))
TOTAL_MINUTES=$((TOTAL_ELAPSED / 60))
TOTAL_SECONDS=$((TOTAL_ELAPSED % 60))

echo "============================="
echo "Total download time: ${TOTAL_MINUTES} minutes and ${TOTAL_SECONDS} seconds"

