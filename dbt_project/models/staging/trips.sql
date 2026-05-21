{{ config(materialized='view') }}

with source_data as (
    select *
    from {{ source('bronze', 'bronze_tripinfo') }}
)

select
    cast(source_data.sim_job_id as varchar) as sim_job_id,
    cast(source_data.id as varchar) as id,
    cast(source_data.depart as double) / 3600 as depart,
    cast(source_data.departPos as double) as departPos,
    cast(source_data.departSpeed as double) * 2.23694 as departSpeed,
    cast(source_data.departDelay as double) as departDelay,
    cast(source_data.arrival as double) / 3600 as arrival,
    cast(source_data.arrivalPos as double) as arrivalPos,
    cast(source_data.arrivalSpeed as double) * 2.23694 as arrivalSpeed,
    cast(source_data.duration as double) / 60 as duration,
    cast(source_data.routeLength as double) * 0.000621371 as routeLength,
    cast(source_data.waitingTime as double) / 60 as waitingTime,
    cast(source_data.waitingCount as double) as waitingCount,
    cast(source_data.stopTime as double) / 60 as stopTime,
    cast(source_data.timeLoss as double) / 60 as timeLoss,
    cast(source_data.rerouteNo as double) as rerouteNo,
    cast(source_data.devices as varchar) as devices,
    cast(source_data.vType as varchar) as vType,
    cast(source_data.speedFactor as double) as speedFactor,
    cast(source_data.vaporized as varchar) as vaporized
from source_data 
