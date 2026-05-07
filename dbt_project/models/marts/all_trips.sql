{{ config(materialized='table') }}

select *
from {{ ref('trips') }}
