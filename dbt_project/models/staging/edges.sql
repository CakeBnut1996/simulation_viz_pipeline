{{ config(materialized='view') }}

with source_data as (
    select *
    from {{ source('bronze', 'bronze_e2') }}
)

select
    cast(source_data.sim_job_id as varchar) as sim_job_id,
    cast(source_data.id as varchar) as id,
    cast(source_data.begin as double) / 3600 as begin,
    cast(source_data.end as double) / 3600 as end,
    cast(source_data.nVehEntered as double) as nVehEntered,
    cast(source_data.nVehLeft as double) as nVehLeft,
    cast(source_data.nVehSeen as double) as nVehSeen,
    case
        when cast(source_data.meanSpeed as double) > 0 then cast(source_data.meanSpeed as double) * 2.23694
        else 0
    end as meanSpeed,
    cast(source_data.meanTimeLoss as double) as meanTimeLoss,
    cast(source_data.meanOccupancy as double) as meanOccupancy,
    cast(source_data.maxOccupancy as double) as maxOccupancy,
    cast(source_data.meanMaxJamLengthInVehicles as double) as meanMaxJamLengthInVehicles,
    cast(source_data.meanMaxJamLengthInMeters as double) * 0.000621371 as meanMaxJamLengthInMiles,
    cast(source_data.maxJamLengthInVehicles as double) as maxJamLengthInVehicles,
    cast(source_data.maxJamLengthInMeters as double) * 0.000621371 as maxJamLengthInMiles,
    cast(source_data.jamLengthInVehiclesSum as double) as jamLengthInVehiclesSum,
    cast(source_data.jamLengthInMetersSum as double) * 0.000621371 as jamLengthInMilesSum,
    cast(source_data.meanHaltingDuration as double) as meanHaltingDuration,
    cast(source_data.maxHaltingDuration as double) as maxHaltingDuration,
    cast(source_data.haltingDurationSum as double) as haltingDurationSum,
    cast(source_data.meanIntervalHaltingDuration as double) as meanIntervalHaltingDuration,
    cast(source_data.maxIntervalHaltingDuration as double) as maxIntervalHaltingDuration,
    cast(source_data.intervalHaltingDurationSum as double) as intervalHaltingDurationSum,
    cast(source_data.startedHalts as double) as startedHalts,
    cast(source_data.meanVehicleNumber as double) as meanVehicleNumber,
    cast(source_data.maxVehicleNumber as double) as maxVehicleNumber
from source_data

