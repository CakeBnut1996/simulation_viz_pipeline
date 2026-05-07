{{ config(materialized='view') }}

with source_data as (
    select *
    from {{ source('bronze_sim', 'bronze_e2') }}
)

select
    cast(sim_job_id as varchar) as sim_job_id,
    cast(source_file_name as varchar) as source_file_name,
    cast(source_file_path as varchar) as source_file_path,
    cast(xml_record_type as varchar) as xml_record_type,
    cast(id as varchar) as id,
    cast(begin as double) as begin,
    cast("end" as double) as "end",
    cast(sampledSeconds as double) as sampledSeconds,
    cast(nVehEntered as double) as nVehEntered,
    cast(nVehLeft as double) as nVehLeft,
    cast(nVehSeen as double) as nVehSeen,
    case
        when cast(meanSpeed as double) > 0 then cast(meanSpeed as double) * 2.23694
        else 0
    end as meanSpeed,
    cast(meanTimeLoss as double) as meanTimeLoss,
    cast(meanOccupancy as double) as meanOccupancy,
    cast(maxOccupancy as double) as maxOccupancy,
    cast(meanMaxJamLengthInVehicles as double) as meanMaxJamLengthInVehicles,
    cast(meanMaxJamLengthInMeters as double) * 0.000621371 as meanMaxJamLengthInMiles,
    cast(maxJamLengthInVehicles as double) as maxJamLengthInVehicles,
    cast(maxJamLengthInMeters as double) * 0.000621371 as maxJamLengthInMiles,
    cast(jamLengthInVehiclesSum as double) as jamLengthInVehiclesSum,
    cast(jamLengthInMetersSum as double) * 0.000621371 as jamLengthInMilesSum,
    cast(meanHaltingDuration as double) as meanHaltingDuration,
    cast(maxHaltingDuration as double) as maxHaltingDuration,
    cast(haltingDurationSum as double) as haltingDurationSum,
    cast(meanIntervalHaltingDuration as double) as meanIntervalHaltingDuration,
    cast(maxIntervalHaltingDuration as double) as maxIntervalHaltingDuration,
    cast(intervalHaltingDurationSum as double) as intervalHaltingDurationSum,
    cast(startedHalts as double) as startedHalts,
    cast(meanVehicleNumber as double) as meanVehicleNumber,
    cast(maxVehicleNumber as double) as maxVehicleNumber
from source_data

