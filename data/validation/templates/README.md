# DPSim Assay Import Templates

These CSV templates define the minimum operator-facing spreadsheet columns for
wet-lab calibration import. They are intentionally plain CSV so they can be
opened in Excel and saved as `.xlsx` for the `spreadsheet` extra path.

Required common columns:

`assay_id,sample_id,target_molecule,polymer_family,mobile_phase,pH,temperature_C,salt_type,salt_concentration_M,replicate,value,unit,LOD,LOQ,instrument,operator,notebook_ref,notes`

Assay-specific condition columns are appended after `notes`.
