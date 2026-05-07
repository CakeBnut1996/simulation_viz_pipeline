{{ config(materialized='table') }}

select *
from {{ ref('edges') }}
