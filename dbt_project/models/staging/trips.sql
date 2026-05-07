{{ config(materialized='view') }}

with source_data as (
    select *
    from {{ source('bronze_sim', 'bronze_tripinfo') }}
)

select
    cast(sim_job_id as varchar) as sim_job_id,
    cast(source_file_name as varchar) as source_file_name,
    cast(source_file_path as varchar) as source_file_path,
    cast(xml_record_type as varchar) as xml_record_type,
    cast(id as varchar) as id,
    cast(depart as double) as depart,
    cast(departLane as varchar) as departLane,
    cast(departPos as double) as departPos,
    cast(departSpeed as double) * 2.23694 as departSpeed,
    cast(departDelay as double) as departDelay,
    cast(arrival as double) as arrival,
    cast(arrivalLane as varchar) as arrivalLane,
    cast(arrivalPos as double) as arrivalPos,
    cast(arrivalSpeed as double) * 2.23694 as arrivalSpeed,
    cast(duration as double) / 60 as duration,
    cast(routeLength as double) * 0.000621371 as routeLength,
    cast(waitingTime as double) / 60 as waitingTime,
    cast(waitingCount as double) as waitingCount,
    cast(stopTime as double) / 60 as stopTime,
    cast(timeLoss as double) / 60 as timeLoss,
    cast(rerouteNo as double) as rerouteNo,
    cast(devices as varchar) as devices,
    cast(vType as varchar) as vType,
    cast(speedFactor as double) as speedFactor,
    cast(vaporized as varchar) as vaporized
from source_data 
