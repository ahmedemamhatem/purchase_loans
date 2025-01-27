// Copyright (c) 2025, Ahmed Emam and contributors
// For license information, please see license.txt

frappe.query_reports["Asset Details Report"] = {
	"filters": [
		{
			"fieldname": "company",
			"label": "Company",
			"fieldtype": "Link",
			"options": "Company",
			"default": frappe.defaults.get_user_default("Company"), 
			"reqd": 1 
		},
		{
			"fieldname": "location",
			"label": "Location",
			"fieldtype": "Link",
			"options": "Location"
		},
		{
			"fieldname": "custodian",
			"label": "Custodian",
			"fieldtype": "Link",
			"options": "Employee"
		},
		{
			"fieldname": "department",
			"label": "Department",
			"fieldtype": "Link",
			"options": "Department"
		},
		{
			"fieldname": "asset_category",
			"label": "Asset Category",
			"fieldtype": "Link",
			"options": "Asset Category"
		}
	]
};
