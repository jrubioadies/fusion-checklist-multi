"""
checklist.py — Configuration Checklist Comparator across Fusion environments.

Each checklist item maps a configuration task to a SQL query (or REST resource)
that counts entities in the environment. The comparator runs ALL items against
all configured environments and produces a dashboard.
"""

# config_method values:
#   "REST"      - Available via fscmRestApi (create/update supported)
#   "FBDI"      - File-Based Data Import (Configuration Workbook / Excel upload)
#   "REST+FBDI" - Both methods available
#   "UI"        - Only via Functional Setup Manager UI (manual)
#
# rest_resource: the fscmRestApi resource name (if REST is available)

CHECKLIST = [
    # --- GL ---
    {"module": "GL", "step": 2, "task": "Manage Legal Entity", "responsible": "",
     "config_method": "FBDI", "rest_resource": None,
     "count_sql": "SELECT COUNT(*) cnt FROM XLE_ENTITY_PROFILES",
     "detail_sql": "SELECT name, legal_entity_identifier, country FROM XLE_ENTITY_PROFILES WHERE rownum<=200"},

    {"module": "GL", "step": 3, "task": "Manage Legal Addresses", "responsible": "",
     "config_method": "FBDI", "rest_resource": None,
     "count_sql": "SELECT COUNT(*) cnt FROM XLE_REGISTRATIONS",
     "detail_sql": "SELECT * FROM XLE_REGISTRATIONS WHERE rownum<=200"},

    {"module": "GL", "step": 5, "task": "Create Primary Ledger", "responsible": "",
     "config_method": "UI", "rest_resource": None,
     "count_sql": "SELECT COUNT(*) cnt FROM GL_LEDGERS",
     "detail_sql": "SELECT ledger_id, name, short_name, currency_code, chart_of_accounts_id FROM GL_LEDGERS WHERE rownum<=200"},

    # --- AP ---
    {"module": "AP", "step": 8, "task": "Manage Business Unit", "responsible": "",
     "config_method": "FBDI", "rest_resource": None,
     "count_sql": "SELECT COUNT(*) cnt FROM FUN_ALL_BUSINESS_UNITS_V WHERE status='A'",
     "detail_sql": "SELECT bu_id, bu_name, status, date_from FROM FUN_ALL_BUSINESS_UNITS_V WHERE status='A' AND rownum<=200"},

    {"module": "AP", "step": 12, "task": "Manage Payables Calendars", "responsible": "",
     "config_method": "UI", "rest_resource": None,
     "count_sql": "SELECT COUNT(DISTINCT period_set_name) cnt FROM GL_PERIODS",
     "detail_sql": "SELECT DISTINCT period_set_name, period_year, COUNT(*) periods FROM GL_PERIODS GROUP BY period_set_name, period_year ORDER BY period_set_name, period_year"},

    {"module": "AP", "step": 13, "task": "Manage Payment Terms", "responsible": "",
     "config_method": "REST+FBDI", "rest_resource": "payablesPaymentTerms",
     "count_sql": "SELECT COUNT(*) cnt FROM AP_TERMS",
     "detail_sql": "SELECT term_id, name, enabled_flag, start_date_active FROM AP_TERMS WHERE rownum<=200 ORDER BY name"},

    {"module": "AP", "step": 14, "task": "Manage Invoice Tolerances", "responsible": "",
     "config_method": "UI", "rest_resource": None,
     "count_sql": "SELECT COUNT(*) cnt FROM AP_TOLERANCE_TEMPLATES",
     "detail_sql": "SELECT * FROM AP_TOLERANCE_TEMPLATES WHERE rownum<=200"},

    {"module": "AP", "step": 19, "task": "Manage Payables Document Sequences", "responsible": "",
     "config_method": "REST", "rest_resource": "documentSequences",
     "count_sql": "SELECT COUNT(*) cnt FROM FND_DOCUMENT_SEQUENCES WHERE application_id=200",
     "detail_sql": "SELECT doc_sequence_id, name, type, initial_value FROM FND_DOCUMENT_SEQUENCES WHERE application_id=200 AND rownum<=200"},

    {"module": "AP", "step": 20, "task": "Manage Distribution Sets", "responsible": "",
     "config_method": "UI", "rest_resource": None,
     "count_sql": "SELECT COUNT(*) cnt FROM AP_DISTRIBUTION_SETS_ALL",
     "detail_sql": "SELECT distribution_set_id, distribution_set_name FROM AP_DISTRIBUTION_SETS_ALL WHERE rownum<=200"},

    {"module": "AP", "step": 21, "task": "Manage Payment Methods", "responsible": "",
     "config_method": "FBDI", "rest_resource": None,
     "count_sql": "SELECT COUNT(*) cnt FROM IBY_PAYMENT_METHODS_B",
     "detail_sql": "SELECT payment_method_code, payment_method_name FROM IBY_PAYMENT_METHODS_B WHERE rownum<=200 ORDER BY payment_method_name"},

    {"module": "AP", "step": 24, "task": "Manage Formats (Payment)", "responsible": "",
     "config_method": "UI", "rest_resource": None,
     "count_sql": "SELECT COUNT(*) cnt FROM IBY_FORMATS_B",
     "detail_sql": "SELECT format_code, format_name, format_type FROM IBY_FORMATS_B WHERE rownum<=200"},

    {"module": "AP", "step": 25, "task": "Manage Payment Process Profiles", "responsible": "",
     "config_method": "UI", "rest_resource": None,
     "count_sql": "SELECT COUNT(*) cnt FROM IBY_PAYMENT_PROFILES",
     "detail_sql": "SELECT payment_profile_id, system_profile_name FROM IBY_PAYMENT_PROFILES WHERE rownum<=200"},

    {"module": "AP", "step": 26, "task": "Manage Banks", "responsible": "",
     "config_method": "REST+FBDI", "rest_resource": "cashBanks",
     "count_sql": "SELECT COUNT(*) cnt FROM CE_BANKS_V",
     "detail_sql": "SELECT bank_party_id, bank_name, bank_number, country FROM CE_BANKS_V WHERE rownum<=200"},

    {"module": "AP", "step": 28, "task": "Manage Bank Branches", "responsible": "",
     "config_method": "REST+FBDI", "rest_resource": "cashBankBranches",
     "count_sql": "SELECT COUNT(*) cnt FROM CE_BANK_BRANCHES_V",
     "detail_sql": "SELECT branch_party_id, bank_branch_name, branch_number, bank_name FROM CE_BANK_BRANCHES_V WHERE rownum<=200"},

    {"module": "AP", "step": 29, "task": "Manage Bank Accounts", "responsible": "",
     "config_method": "REST+FBDI", "rest_resource": "cashBankAccounts",
     "count_sql": "SELECT COUNT(*) cnt FROM CE_BANK_ACCOUNTS",
     "detail_sql": "SELECT bank_account_id, bank_account_name, bank_account_num, currency_code FROM CE_BANK_ACCOUNTS WHERE rownum<=200"},

    # --- Tax ---
    {"module": "AP, AR", "step": 40, "task": "Manage Tax Rates", "responsible": "",
     "config_method": "FBDI", "rest_resource": None,
     "count_sql": "SELECT COUNT(*) cnt FROM ZX_RATES_B",
     "detail_sql": "SELECT tax_rate_id, tax_rate_code, percentage_rate, active_flag FROM ZX_RATES_B WHERE rownum<=200"},

    {"module": "AP, AR", "step": 42, "task": "Manage Tax Regimes", "responsible": "",
     "config_method": "FBDI", "rest_resource": None,
     "count_sql": "SELECT COUNT(*) cnt FROM ZX_REGIMES_B",
     "detail_sql": "SELECT tax_regime_id, tax_regime_code, effective_from FROM ZX_REGIMES_B WHERE rownum<=200"},

    # --- AR ---
    {"module": "AR", "step": 48, "task": "Manage Receivables System Options", "responsible": "",
     "config_method": "UI", "rest_resource": None,
     "count_sql": "SELECT COUNT(*) cnt FROM AR_SYSTEM_PARAMETERS_ALL",
     "detail_sql": "SELECT * FROM AR_SYSTEM_PARAMETERS_ALL WHERE rownum<=50"},

    {"module": "AR", "step": 49, "task": "Manage Receivables Activities", "responsible": "",
     "config_method": "FBDI", "rest_resource": None,
     "count_sql": "SELECT COUNT(*) cnt FROM AR_RECEIVABLES_TRX_ALL",
     "detail_sql": "SELECT receivables_trx_id, name, type, status FROM AR_RECEIVABLES_TRX_ALL WHERE rownum<=200"},

    {"module": "AR", "step": 52, "task": "Manage Transaction Types", "responsible": "",
     "config_method": "FBDI", "rest_resource": None,
     "count_sql": "SELECT COUNT(*) cnt FROM RA_CUST_TRX_TYPES_ALL",
     "detail_sql": "SELECT cust_trx_type_id, name, type, status FROM RA_CUST_TRX_TYPES_ALL WHERE rownum<=200"},

    {"module": "AR", "step": 55, "task": "Manage Receivables Payment Terms", "responsible": "",
     "config_method": "FBDI", "rest_resource": None,
     "count_sql": "SELECT COUNT(*) cnt FROM RA_TERMS",
     "detail_sql": "SELECT term_id, name, start_date_active, end_date_active FROM RA_TERMS WHERE rownum<=200"},

    {"module": "AR", "step": 60, "task": "Manage Receivables Document Sequences", "responsible": "",
     "config_method": "REST", "rest_resource": "documentSequences",
     "count_sql": "SELECT COUNT(*) cnt FROM FND_DOCUMENT_SEQUENCES WHERE application_id=222",
     "detail_sql": "SELECT doc_sequence_id, name, type, initial_value FROM FND_DOCUMENT_SEQUENCES WHERE application_id=222 AND rownum<=200"},

    {"module": "AR", "step": 62, "task": "Manage Standard Memo Lines", "responsible": "",
     "config_method": "FBDI", "rest_resource": None,
     "count_sql": "SELECT COUNT(*) cnt FROM AR_MEMO_LINES_ALL_B",
     "detail_sql": "SELECT memo_line_id, name, line_type FROM AR_MEMO_LINES_ALL_B WHERE rownum<=200"},

    {"module": "AR", "step": 63, "task": "Manage Receipt Classes and Methods", "responsible": "",
     "config_method": "FBDI", "rest_resource": None,
     "count_sql": "SELECT COUNT(*) cnt FROM AR_RECEIPT_METHODS",
     "detail_sql": "SELECT receipt_method_id, name, receipt_class_id, start_date, end_date FROM AR_RECEIPT_METHODS WHERE rownum<=200"},

    {"module": "AR", "step": 65, "task": "Manage Receipt Sources", "responsible": "",
     "config_method": "FBDI", "rest_resource": None,
     "count_sql": "SELECT COUNT(*) cnt FROM AR_BATCH_SOURCES_ALL",
     "detail_sql": "SELECT batch_source_id, name, type, status FROM AR_BATCH_SOURCES_ALL WHERE rownum<=200"},

    {"module": "AR", "step": 66, "task": "Manage Transaction Sources", "responsible": "",
     "config_method": "FBDI", "rest_resource": None,
     "count_sql": "SELECT COUNT(*) cnt FROM RA_BATCH_SOURCES_ALL",
     "detail_sql": "SELECT batch_source_id, name, type, status FROM RA_BATCH_SOURCES_ALL WHERE rownum<=200"},

    # --- AF (Fixed Assets) ---
    {"module": "AF", "step": 84, "task": "Manage Prorate Conventions", "responsible": "",
     "config_method": "UI", "rest_resource": None,
     "count_sql": "SELECT COUNT(*) cnt FROM FA_CONVENTIONS",
     "detail_sql": "SELECT prorate_convention_code, description FROM FA_CONVENTIONS WHERE rownum<=200"},

    {"module": "AF", "step": 85, "task": "Manage Asset Book", "responsible": "",
     "config_method": "FBDI", "rest_resource": None,
     "count_sql": "SELECT COUNT(*) cnt FROM FA_BOOK_CONTROLS",
     "detail_sql": "SELECT book_type_code, book_type_name, book_class FROM FA_BOOK_CONTROLS WHERE rownum<=200"},

    {"module": "AF", "step": 96, "task": "Manage Depreciation Methods", "responsible": "",
     "config_method": "UI", "rest_resource": None,
     "count_sql": "SELECT COUNT(*) cnt FROM FA_METHODS",
     "detail_sql": "SELECT method_code, name, life_in_months FROM FA_METHODS WHERE rownum<=200"},

    {"module": "AF", "step": 97, "task": "Manage Asset Categories", "responsible": "",
     "config_method": "FBDI", "rest_resource": None,
     "count_sql": "SELECT COUNT(*) cnt FROM FA_CATEGORIES_B",
     "detail_sql": "SELECT category_id, segment1, segment2, segment3, enabled_flag FROM FA_CATEGORIES_B WHERE rownum<=200"},

    # --- CM (Cash Management) ---
    {"module": "CM", "step": 101, "task": "Manage Banks", "responsible": "",
     "config_method": "REST+FBDI", "rest_resource": "cashBanks",
     "count_sql": "SELECT COUNT(*) cnt FROM CE_BANKS_V",
     "detail_sql": "SELECT bank_party_id, bank_name, bank_number, country FROM CE_BANKS_V WHERE rownum<=200"},

    {"module": "CM", "step": 102, "task": "Manage Bank Branches", "responsible": "",
     "config_method": "REST+FBDI", "rest_resource": "cashBankBranches",
     "count_sql": "SELECT COUNT(*) cnt FROM CE_BANK_BRANCHES_V",
     "detail_sql": "SELECT branch_party_id, bank_branch_name, branch_number FROM CE_BANK_BRANCHES_V WHERE rownum<=200"},

    {"module": "CM", "step": 103, "task": "Manage Bank Accounts", "responsible": "",
     "config_method": "REST+FBDI", "rest_resource": "cashBankAccounts",
     "count_sql": "SELECT COUNT(*) cnt FROM CE_BANK_ACCOUNTS",
     "detail_sql": "SELECT bank_account_id, bank_account_name, bank_account_num, currency_code FROM CE_BANK_ACCOUNTS WHERE rownum<=200"},

    {"module": "CM", "step": 105, "task": "Manage Bank Statement Transaction Codes", "responsible": "",
     "config_method": "UI", "rest_resource": None,
     "count_sql": "SELECT COUNT(*) cnt FROM CE_TRANSACTION_CODES",
     "detail_sql": "SELECT trx_code_id, trx_code, description FROM CE_TRANSACTION_CODES WHERE rownum<=200"},

    {"module": "CM", "step": 109, "task": "Manage Reconciliation Tolerance Rules", "responsible": "",
     "config_method": "UI", "rest_resource": None,
     "count_sql": "SELECT COUNT(*) cnt FROM CE_RECON_TOLERANCE_RULES",
     "detail_sql": "SELECT * FROM CE_RECON_TOLERANCE_RULES WHERE rownum<=200"},

    # --- Procurement ---
    {"module": "Procurement", "step": 1, "task": "Manage Business Unit (Procurement)", "responsible": "",
     "config_method": "FBDI", "rest_resource": None,
     "count_sql": "SELECT COUNT(*) cnt FROM FUN_ALL_BUSINESS_UNITS_V WHERE status='A'",
     "detail_sql": "SELECT bu_id, bu_name, status FROM FUN_ALL_BUSINESS_UNITS_V WHERE status='A' AND rownum<=200"},

    {"module": "Procurement", "step": 5, "task": "Manage Inventory Organizations", "responsible": "",
     "config_method": "REST+FBDI", "rest_resource": "inventoryOrganizations",
     "count_sql": "SELECT COUNT(*) cnt FROM INV_ORGANIZATION_DEFINITIONS_V",
     "detail_sql": "SELECT organization_id, organization_code, organization_name FROM INV_ORGANIZATION_DEFINITIONS_V WHERE rownum<=200"},

    {"module": "Procurement", "step": 9, "task": "Manage Locations", "responsible": "",
     "config_method": "FBDI", "rest_resource": None,
     "count_sql": "SELECT COUNT(*) cnt FROM PER_LOCATIONS",
     "detail_sql": "SELECT location_id, location_code, location_name, country FROM PER_LOCATIONS WHERE rownum<=200"},

    # --- Intercompany ---
    {"module": "Intercompany", "step": 77, "task": "Manage Intercompany Balancing Rules", "responsible": "",
     "config_method": "UI", "rest_resource": None,
     "count_sql": "SELECT COUNT(*) cnt FROM FUN_BAL_INTER_RULES",
     "detail_sql": "SELECT * FROM FUN_BAL_INTER_RULES WHERE rownum<=200"},
]
