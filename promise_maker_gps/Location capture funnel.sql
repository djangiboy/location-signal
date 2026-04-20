-- =============================================================================
-- DELHI ZONE • DEC 2025 • INSTALLED vs DECLINED COHORT ANALYSIS
-- Keyed on MOBILE (unique identifier)
-- Snowflake JSON syntax
-- =============================================================================

WITH 
-- -----------------------------------------------------------------------------
-- STEP 1: Base cohort — Dec 2025 + full booking fee captured
-- -----------------------------------------------------------------------------
fee_captured AS (
    SELECT
        mobile,
        MIN(added_time) AS fee_captured_at
    FROM booking_logs
    WHERE event_name = 'lead_state_changed'
    AND PARSE_JSON(data):lead_state::STRING = 'booking_verified'
      AND added_time >= '2025-12-01'
      AND added_time <  '2026-01-01'
    GROUP BY mobile
),
-- -----------------------------------------------------------------------------
-- STEP 2: Booking lat/lng — lead_state_changed where state = 'serviceable'
-- -----------------------------------------------------------------------------
booking_location AS (
    SELECT
        mobile,
        booking_lat,
        booking_lng,
        added_time
    FROM (
        SELECT
            mobile,
            TRY_CAST(PARSE_JSON(data):lat::STRING AS DOUBLE) AS booking_lat,
            TRY_CAST(PARSE_JSON(data):lng::STRING AS DOUBLE) AS booking_lng,
            added_time,
            ROW_NUMBER() OVER (PARTITION BY mobile ORDER BY added_time DESC) AS rn
        FROM booking_logs
        WHERE event_name = 'lead_state_changed'
          AND PARSE_JSON(data):lead_state::STRING = 'serviceable'
          AND added_time >= '2025-12-01'
          AND added_time <  '2026-01-01'
    )
    WHERE rn = 1
),

-- -----------------------------------------------------------------------------
-- STEP 3: Delhi zone filter
-- -----------------------------------------------------------------------------
delhi_mobiles AS (
    SELECT DISTINCT mobile
    FROM booking_logs
    WHERE added_time >= '2025-12-01'
      AND added_time <  '2026-01-01'
      AND (
            LOWER(PARSE_JSON(data):city::STRING)  = 'delhi'
         OR LOWER(PARSE_JSON(data):zone::STRING)  = 'delhi'
         OR LOWER(PARSE_JSON(data):state::STRING) LIKE '%delhi%'
      )
),

-- -----------------------------------------------------------------------------
-- STEP 4: Final lead state per mobile
-- ----------------------------------------------------------------------------
final_state AS (
    SELECT
        mobile,
        lead_state,
        decline_reason,
        state_at
    FROM (
        SELECT
            mobile,
            PARSE_JSON(data):lead_state::STRING     AS lead_state,
            PARSE_JSON(data):reasons::STRING        AS decline_reason,
            added_time                              AS state_at,
            ROW_NUMBER() OVER (PARTITION BY mobile ORDER BY added_time DESC) AS rn
        FROM booking_logs
        WHERE event_name = 'lead_state_changed'
          AND PARSE_JSON(data):lead_state::STRING IN ('installed')
          AND added_time >= '2025-12-01'
          AND added_time <  '2026-01-01'

        UNION ALL

        SELECT
            mobile,
            'declined'                              AS lead_state,
            TRY_PARSE_JSON(data):remarks::STRING    AS decline_reason,
            added_time,                            
            ROW_NUMBER() OVER (PARTITION BY mobile ORDER BY added_time DESC) AS rn
        FROM task_logs
        WHERE event_name = 'DECLINED'
          AND added_time >= '2025-12-01'
          AND added_time <  '2026-01-01' and TRY_PARSE_JSON(data):source::STRING = 'Declined_post_Assigned'
          AND mobile not in 
          (
                SELECT
                    mobile
                FROM booking_logs
                WHERE event_name = 'lead_state_changed'
                  AND PARSE_JSON(data):lead_state::STRING IN ('installed')
                  AND added_time >= '2025-12-01'
                  AND added_time <  '2026-01-01'
                  group by mobile
          )


    )
    WHERE rn = 1
),

-- -----------------------------------------------------------------------------
-- STEP 5: Install lat/lng — from DEVICE event
-- extraData is a STRINGIFIED JSON inside data, so parse it twice
-- -----------------------------------------------------------------------------
install_location AS (
    SELECT *
    FROM (
        SELECT
            mobile,
            TRY_CAST(PARSE_JSON(data):lat::STRING AS DOUBLE) AS install_lat,
            TRY_CAST(PARSE_JSON(data):lng::STRING AS DOUBLE) AS install_lng,
            added_time,
            ROW_NUMBER() OVER (PARTITION BY mobile ORDER BY added_time) AS rn
        FROM booking_logs
        WHERE event_name = 'wifi_connected_location_captured'
    )
    WHERE rn = 1
    and cast(added_time as date) between '2025-12-01' and '2026-01-10'
),



-- -----------------------------------------------------------------------------
-- STEP 6: Booking accuracy
-- -----------------------------------------------------------------------------
booking_accuracy AS (
    SELECT
        mobile,
        booking_accuracy
    FROM (
        SELECT
            mobile,
            TRY_CAST(PARSE_JSON(data):accuracy_in_meters::STRING AS DOUBLE) AS booking_accuracy,
            ROW_NUMBER() OVER (PARTITION BY mobile ORDER BY added_time ASC) AS rn
        FROM booking_logs
        WHERE event_name = 'location_accuracy_captured'
          AND added_time >= '2025-12-01'
          AND added_time <  '2026-01-01'
    )
    WHERE rn = 1
),

-- -----------------------------------------------------------------------------
-- STEP 7: Assemble master cohort
-- -----------------------------------------------------------------------------
cohort AS (
    SELECT
        fc.mobile,
        fc.fee_captured_at,
        bl.booking_lat,
        bl.booking_lng,
        ba.booking_accuracy,
        case when fs.lead_state = 'installed' then il.install_lat else null end as installed_lat,
        case when fs.lead_state = 'installed' then il.install_lng else null end as install_lng,
        fs.lead_state,
        fs.decline_reason,

        CASE
            WHEN HOUR(CONVERT_TIMEZONE('UTC','Asia/Kolkata', fc.fee_captured_at)) >= 22 
              OR HOUR(CONVERT_TIMEZONE('UTC','Asia/Kolkata', fc.fee_captured_at)) < 4  
                THEN '22-04_at_home'
        
            WHEN HOUR(CONVERT_TIMEZONE('UTC','Asia/Kolkata', fc.fee_captured_at)) >= 4  
             AND HOUR(CONVERT_TIMEZONE('UTC','Asia/Kolkata', fc.fee_captured_at)) < 6  
                THEN '04-06_early'
        
            WHEN HOUR(CONVERT_TIMEZONE('UTC','Asia/Kolkata', fc.fee_captured_at)) >= 6  
             AND HOUR(CONVERT_TIMEZONE('UTC','Asia/Kolkata', fc.fee_captured_at)) < 9  
                THEN '06-09_morning'
        
            WHEN HOUR(CONVERT_TIMEZONE('UTC','Asia/Kolkata', fc.fee_captured_at)) >= 9  
             AND HOUR(CONVERT_TIMEZONE('UTC','Asia/Kolkata', fc.fee_captured_at)) < 13 
                THEN '09-13_workday_am'
        
            WHEN HOUR(CONVERT_TIMEZONE('UTC','Asia/Kolkata', fc.fee_captured_at)) >= 13 
             AND HOUR(CONVERT_TIMEZONE('UTC','Asia/Kolkata', fc.fee_captured_at)) < 16 
                THEN '13-16_afternoon'
        
            WHEN HOUR(CONVERT_TIMEZONE('UTC','Asia/Kolkata', fc.fee_captured_at)) >= 16 
             AND HOUR(CONVERT_TIMEZONE('UTC','Asia/Kolkata', fc.fee_captured_at)) < 19 
                THEN '16-19_evening'
        
            WHEN HOUR(CONVERT_TIMEZONE('UTC','Asia/Kolkata', fc.fee_captured_at)) >= 19 
             AND HOUR(CONVERT_TIMEZONE('UTC','Asia/Kolkata', fc.fee_captured_at)) < 22 
                THEN '19-22_night'
        END AS time_bucket,

        CASE
            WHEN fs.lead_state = 'installed' and il.install_lat IS NOT NULL AND bl.booking_lat IS NOT NULL THEN
                2 * 6371000 * ASIN(SQRT(
                    POWER(SIN(RADIANS(il.install_lat - bl.booking_lat) / 2), 2)
                    + COS(RADIANS(bl.booking_lat)) * COS(RADIANS(il.install_lat))
                    * POWER(SIN(RADIANS(il.install_lng - bl.booking_lng) / 2), 2)
                ))
            ELSE NULL
        END AS install_drift_meters

    FROM fee_captured fc
    INNER JOIN delhi_mobiles     db ON db.mobile = fc.mobile
    LEFT  JOIN booking_location  bl ON bl.mobile = fc.mobile
    LEFT  JOIN booking_accuracy  ba ON ba.mobile = fc.mobile
    LEFT  JOIN install_location  il ON il.mobile = fc.mobile
    LEFT  JOIN final_state       fs ON fs.mobile = fc.mobile
    WHERE fs.lead_state IN ('installed', 'declined')
)

SELECT * FROM cohort;