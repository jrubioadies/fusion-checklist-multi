#!/usr/bin/env python3
"""
fsm_checklist.py — Genera un checklist a partir de un Implementation Project de FSM.

Lee de la instancia la jerarquía de listas/tareas del proyecto (ASM_*/ASK_*) y
asigna a cada tarea una SQL de detalle:

  1. Profile options que gestiona la tarea (ASK_BO_ATTRIBUTE_VALUES.profileOptionName)
  2. Lookup types de la tarea (ASK_BO_ATTRIBUTE_VALUES.lookupType o parámetros
     lookupTypes=/ParentLookupType=/ChildLookupType= del task flow)
  3. Profiles por Business Unit (parámetro profileList= → SVC_BU_PROFILE_VALUES)
  4. SQL manual por tarea (MANUAL, abajo) para objetos con tabla propia
  5. Resto: tarea solo UI (sin SQL; aparece en el checklist como manual)

La SQL de conteo es COUNT(*) sobre la de detalle. En el detalle la 1ª columna es
la clave de comparación entre entornos y la 2ª el contexto.

Uso:
  python3 tools/fsm_checklist.py --project IMPLEMENTATION_PROJECT_1 --client pinero --env TEST \\
      --name Service --out checklists/service.json [--validate]
  (--fusion-bip-env TEST usa ~/.config/fusion-bip/config.json en vez de un perfil de cliente)
"""
import argparse, csv, io, json, os, re, sys, warnings
from collections import OrderedDict
from pathlib import Path

warnings.filterwarnings("ignore")
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from fusion_client import bip as fbip  # noqa: E402

SEED = "SEED_DATA_FROM_APPLICATION"

# SQL de detalle por tarea (clave, contexto). Solo tablas verificadas en Fusion.
CATS = ("SELECT b.category_short_name{bu} k, t.category_name||' ('||b.enabled_flag||')' ctx "
        "FROM SVC_CATEGORIES_B b LEFT JOIN SVC_CATEGORIES_TL t ON t.category_id=b.category_id "
        "AND t.language=USERENV('LANG') WHERE b.deleted_flag='N' AND b.stripe_cd='{stripe}'")
BU_SUFFIX = "||' @ '||(SELECT bu_name FROM FUN_ALL_BUSINESS_UNITS_V u WHERE u.bu_id=b.bu_org_id)"
MILESTONES = ("SELECT m.milestone_code||' · '||m.object_name{bu} k, m.milestone_label||' ('||NVL(m.disabled_flag,'N')||')' ctx "
              "FROM SVC_MILESTONE_CONFIGS m WHERE m.deleted_flag='N'")
CUSTOM_PROFILES = ("SELECT o.profile_option_name||' ['||v.level_name||CASE WHEN v.level_name<>'SITE' THEN ':'||v.level_value END"
                   "||'] = '||v.profile_option_value k, v.last_updated_by ctx FROM FND_PROFILE_OPTION_VALUES v "
                   "JOIN FND_PROFILE_OPTIONS_B o ON o.profile_option_id=v.profile_option_id "
                   f"WHERE v.last_updated_by<>'{SEED}'")

MANUAL = {
    # ── Company profile ──
    "XLE_MANAGE_LEGAL_JURISDICTIONS": "SELECT name k, legislative_cat_code ctx FROM XLE_JURISDICTIONS_VL",
    "XLE_MANAGE_LEGAL_ADDRESSES": "SELECT registered_name||' ['||registration_number||']' k, source_table ctx FROM XLE_REGISTRATIONS",
    "XLE_MANAGE_LEGAL_ENTITY": "SELECT name k, legal_entity_identifier ctx FROM XLE_ENTITY_PROFILES",
    "FUN_MANAGE_BUSINESS_UNIT": "SELECT bu_name k, status ctx FROM FUN_ALL_BUSINESS_UNITS_V",
    "FND_MANAGE_CURRENCIES": "SELECT currency_code k, name ctx FROM FND_CURRENCIES_VL WHERE enabled_flag='Y'",
    "GL_MANAGE_ACCOUNTING_CALENDARS": "SELECT period_set_name k, description ctx FROM GL_PERIOD_SETS",
    "HZ_MANAGE_GEOGRAPHIES": ("SELECT country_code||' · '||geography_type||' = '||COUNT(*) k, geography_use ctx FROM HZ_GEOGRAPHIES "
                              "WHERE geography_use='MASTER_REF' GROUP BY country_code, geography_type, geography_use"),
    "FND_MANAGE_TERRITORIES": "SELECT territory_code k, territory_short_name ctx FROM FND_TERRITORIES_VL WHERE enabled_flag='Y'",
    # ── Users and security ──
    "PER_MANAGE_JOB": ("SELECT job_code k, name ctx FROM PER_JOBS_F_VL "
                       "WHERE TRUNC(SYSDATE) BETWEEN effective_start_date AND effective_end_date"),
    "PER_MANAGE_HCM_ROLE_PROVISIONING_RULES": "SELECT mapping_name k, assignment_status ctx FROM PER_ROLE_MAPPINGS",
    "ASXS_MANAGE_JOB_ROLES": "SELECT code k, role_type_code ctx FROM ASE_ROLE_VL WHERE NVL(is_seeded,'N')='N'",
    "ASXS_MANAGE_DUTIES": "SELECT code k, role_type_code ctx FROM ASE_ROLE_VL WHERE NVL(is_seeded,'N')='N'",
    "PER_MANAGE_USERS": "SELECT username k, active_flag ctx FROM PER_USERS",
    "ASXS_MANAGE_DATA_SECURITY_POLICIES": f"SELECT name k, grant_type ctx FROM FND_GRANTS WHERE created_by<>'{SEED}'",
    "HZ_MANAGE_RESOURCE_ROLES": "SELECT role_code k, role_type_code ctx FROM JTF_RS_ROLES_B",
    "HZ_MANAGE_TRADING_COMMUNITY_SOURCE_SYSTEMS": "SELECT orig_system k, orig_system_type ctx FROM HZ_ORIG_SYSTEMS_B",
    # ── Service requests ──
    "ORA_SVC_SERVICE_REQUEST_CATEGORIES": CATS.format(bu="", stripe="ORA_SVC_CRM"),
    "ORA_SVC_MANAGE_SR_CATEGORIES_FOR_HRHD": CATS.format(bu="", stripe="ORA_SVC_HCM"),
    "ORA_MANAGE_CATEGORIES_FOR_CASES": CATS.format(bu="", stripe="ORA_SVC_CASE"),
    "ORA_SVC_MANAGE_SERVICE_CATEGORIES_FOR_BU": CATS.format(bu=BU_SUFFIX, stripe="ORA_SVC_CRM"),
    "ORA_SVC_MANAGE_HRHD_SERVICE_CATEGORIES_FOR_BU": CATS.format(bu=BU_SUFFIX, stripe="ORA_SVC_HCM"),
    "ORA_MANAGE_OBJECT_LINK_TYPES": "SELECT short_name k, name||' ('||enabled_flag||')' ctx FROM SVC_OBJECT_LINK_TYPES",
    "ORA_MANAGE_QUEUES_FOR_CASES": ("SELECT queue_number k, queue_name||' ('||enabled_flag||')' ctx FROM SVC_QUEUES "
                                    "WHERE deleted_flag='N' AND stripe_cd='ORA_SVC_CASE'"),
    # ── Catalog ──
    "QSC_MANAGE_PRODUCT_GROUPS": "SELECT internal_name k, ref_number ctx FROM QSC_PROD_GROUPS_B",
    "QSC_MANAGE_PRODUCT_GROUP_USAGE": "SELECT usage_code k, usage_name ctx FROM QSC_PROD_GRP_USAGE",
    # ── Channels ──
    "ORA_SVC_MANAGE_COMM_CHANNELS": ("SELECT b.channel_short_name k, b.channel_type_cd||' · '||t.display_name||' ('||b.enabled_flag||')' ctx "
                                     "FROM SVC_CHANNELS_B b LEFT JOIN SVC_CHANNELS_TL t ON t.channel_id=b.channel_id "
                                     "AND t.language=USERENV('LANG') WHERE b.deleted_flag='N'"),
    "ORA_SVC_CONFIGURE_CALL_FLOW_PARMS": ("SELECT appl_classification_cd||' · '||wrap_up_type_cd k, default_flag ctx "
                                          "FROM SVC_MCA_CALL_FLOW_CONFIG WHERE deleted_flag='N'"),
    "ORA_SVC_MANAGE_SCREEN_POP_CONFIG": "SELECT name k, display_name ctx FROM SVC_MCA_CONFIGURATION WHERE deleted_flag='N'",
    "ORA_SVC_MANAGE_MEDIA_TOOLBAR_CONFIG": "SELECT name k, vendor||' ('||active_flag||')' ctx FROM SVC_MCA_TOOLBAR WHERE deleted_flag='N'",
    "ORA_SVC_MANAGE_EMAIL_FILTERS": ("SELECT filter_type_cd||' · '||field_name||' · '||pattern k, action_cd ctx "
                                     "FROM SVC_INBOUND_MSG_FILTERS WHERE deleted_flag='N'"),
    "ORA_SVC_EMAIL_CONFIGURATION_AND_VALIDATION": "SELECT inbound_email_address k, activation_date ctx FROM SVC_CHANNEL_EMAIL_CONFIGS",
    "ORA_MANAGE_OUTBOUND_MESSAGE_CONFIGURATION": ("SELECT sender_email_address||' · '||delivery_service_type_cd k, enabled_flag ctx "
                                                  "FROM SVC_OUTBOUND_CHNL_CONFIGS"),
    "ORA_SVC_MANAGE_CAPACITIES": ("SELECT c.object_type_cd||' @ '||NVL((SELECT bu_name FROM FUN_ALL_BUSINESS_UNITS_V u WHERE u.bu_id=c.bu_org_id),'-') k, "
                                  "c.status_cd ctx FROM SVC_OBJECT_CAPACITIES c WHERE c.deleted_flag='N'"),
    "ORA_SVC_MANAGE_SERVICE_REQUEST_ASSIGNMENT_OBJECTS": ("SELECT asgn_object_code k, record_status ctx FROM MOW_ASGN_OBJECTS_B "
                                                          "WHERE owner_module='svcMgmt'"),
    "ORA_SVC_MANAGE_SERVICE_REQUEST_ASSIGNMENT_RULES": ("SELECT rule_set_group_code k, NVL(inactive_flag,'N') ctx FROM MOW_RULE_SET_GROUPS_B "
                                                        "WHERE owner_module='svcMgmt'"),
    "ORA_SVC_MANAGE_MILESTONE_CONFIG": MILESTONES.format(bu=""),
    "ORA_SVC_MANAGE_SVC_MILESTONE_CONFIG_FOR_BU": MILESTONES.format(
        bu="||' @ '||NVL((SELECT bu_name FROM FUN_ALL_BUSINESS_UNITS_V u WHERE u.bu_id=m.bu_org_id),'-')"),
    # ── Work orders ──
    "ORA_MANAGE_WORK_ORDER_LINK_TEMPLATES": ("SELECT link_template_number k, link_template_cat_cd||' ('||active_flag||')' ctx "
                                             "FROM SVC_WO_LINK_TEMPLATES_B"),
    "ORA_MANAGE_TYPES_OF_WORK_ORDERS": ("SELECT wo_activity_type_cd k, fs_activity_type_cd||' ('||enabled_flag||')' ctx "
                                        "FROM SVC_WO_ACTIVITY_TYPES_B"),
    # ── Action plans ──
    "ORA_SVC_MANAGE_ACTION_PLAN_ACTION_STATUS_MAPPING": ("SELECT name k, action_status_cd ctx FROM SVC_AP_STATUS_CONDITIONS "
                                                         "WHERE deleted_flag='N'"),
    "ORA_SVC_MANAGE_ACTION_PLAN_ACTIONS": ("SELECT action_number k, name ctx FROM SVC_AP_ACTIONS "
                                           "WHERE deleted_flag='N' AND catalog_flag='Y'"),
    "ORA_SVC_MANAGE_ACTION_PLAN_TEMPLATES": ("SELECT template_number k, name||' ('||enabled_flag||')' ctx FROM SVC_AP_TEMPLATES "
                                             "WHERE deleted_flag='N'"),
    "ORA_MANAGE_ACTION_PLAN_PROCESS_METADATA": "SELECT process_metadata_number k, process_name ctx FROM SVC_PROCESS_METADATA",
    # ── Surveys ──
    "ORA_SVC_MANAGE_SURVEY_CONFIGURATIONS": "SELECT survey_config_number k, name||' · '||vendor_cd ctx FROM SVC_SURVEY_CONFIGS",
    "ORA_SVC_MANAGE_SURVEY_TEMPLATES": ("SELECT survey_number k, name||' ('||active_flag||')' ctx FROM SVC_SURVEYS "
                                        "WHERE stripe_cd='ORA_SVC_CRM'"),
    "ORA_MANAGE_SURVEY_TEMPLATES_FOR_HR_HELP_DESK": ("SELECT survey_number k, name||' ('||active_flag||')' ctx FROM SVC_SURVEYS "
                                                     "WHERE stripe_cd='ORA_SVC_HCM'"),
    # ── Productivity ──
    "ORA_SVC_MANAGE_SERVICE_REQUEST_KEYBOARD_SHORTCUTS": ("SELECT shortcut_combination||' · '||action_id k, custom_flag ctx "
                                                          "FROM SVC_HOTKEY_SHORTCUTS WHERE NVL(invalid_flag,'N')='N'"),
    "ORA_SVC_MANAGE_SERVICE_REQUEST_DYNAMIC_LINKS": "SELECT label||' · '||pattern k, object_type ctx FROM SVC_DYN_LINK_PATTERNS",
    "ORA_SVC_MANAGE_PASSIVE_BEACON_CONFIGURATION": "SELECT service_name k, service_state_cd ctx FROM SVC_BCN_SERVICES",
    "ORA_SVC_MANAGE_TAGS": "SELECT tag||' = '||COUNT(*) k, object_type_cd ctx FROM SVC_TAGS WHERE deleted_flag='N' GROUP BY tag, object_type_cd",
    "ORA_MANAGE_COLLABORATION_ACTIONS": ("SELECT collab_action_number k, collab_action_name ctx FROM SVC_COLLAB_ACTIONS "
                                         "WHERE deleted_flag='N'"),
    "ORA_ZCA_MANAGE_PUID_SEQ": "SELECT object_code k, prefix||' / '||radix ctx FROM ZCA_PUID_CONFIG",
    # ── Knowledge ──
    "ORA_CSO_LOCALES_MGMT": "SELECT locale_code k, active ctx FROM CSO_LOCALE",
    "ORA_MANAGE_KNOWLEDGE_WORKFLOWS": "SELECT reference_key k, enabled_flag ctx FROM CSO_WORKFLOW WHERE NVL(deleted_flag,'N')='N'",
    "ORA_CSO_CONTENT_TYPES_MGMT": "SELECT reference_key k, NULL ctx FROM CSO_CHANNEL",
    "ORA_CSO_CONTENT_TYPES_INDEXING_MGMT_REDWOOD": "SELECT reference_key k, NULL ctx FROM CSO_CHANNEL",
    "ORA_CSO_ARTICLE_STATUS_MGMT": "SELECT reference_key k, active ctx FROM CSO_ARTICLE_STATUS",
    "ORA_CSO_SEARCH_DICT_MGMT": "SELECT search_language||' = '||COUNT(*) k, NULL ctx FROM CSO_SCH_SYNSET GROUP BY search_language",
    "ORA_CSO_KNOWLEDGE_RICH_TEXT_EDITOR": "SELECT stripe_cd k, active ctx FROM CSO_RICHTEXT_EDITOR_CONFIG",
    "ORA_MANAGE_KNOWLEDGE_VOCABULARY": "SELECT word||' ['||locale||']' k, type ctx FROM CSO_SCH_VOCABULARY",
    # ── Digital Customer Service ──
    "ORA_CREATE_DIGITAL_CUSTOMER_SERVICE_CUSTOM_ROLE_MAPPING": "SELECT css_role_cd||' → '||idp_role_code k, NULL ctx FROM SVC_CSS_IDP_ROLE_MAPPINGS",
    # ── Common reference objects ──
    "ORA_SVC_MANAGE_SERVICE_NOTE_TYPE_MAPPING": ("SELECT source_object_code||' → '||mapped_lookup_code k, default_flag ctx FROM ZMM_OBJECT_LOOKUP_MAPPINGS "
                                                 "WHERE mapping_type_code='ZMM_NOTE_TYPE'"),
    "FND_MANAGE_REFERENCE_DATA_SETS": "SELECT set_code k, set_name ctx FROM FND_SETID_SETS_VL",
    "FND_MANAGE_REFERENCE_DATA_SET_ASSIGNMENTS": ("SELECT reference_group_name||' → '||set_id||' = '||COUNT(*) k, determinant_type ctx "
                                                  "FROM FND_SETID_ASSIGNMENTS GROUP BY reference_group_name, set_id, determinant_type"),
    "FND_MANAGE_ISO_LANGUAGES": "SELECT iso_language_3 k, iso_language_2 ctx FROM FND_ISO_LANGUAGES_B",
    "FND_MANAGE_LANGUAGES": "SELECT language_code k, installed_flag ctx FROM FND_LANGUAGES_B WHERE installed_flag IN ('B','I')",
    "FND_MANAGE_INDUSTRIES": "SELECT industry_code k, enabled_flag ctx FROM FND_INDUSTRIES_B WHERE enabled_flag='Y'",
    "FND_MANAGE_NATURAL_LANGUAGES": "SELECT language_code k, iso_territory ctx FROM FND_NATURAL_LANGUAGES_B WHERE enabled_flag='Y'",
    "FND_MANAGE_TIMEZONES": "SELECT timezone_code k, enabled_flag ctx FROM FND_TIMEZONES_B WHERE enabled_flag='Y'",
    "FND_MANAGE_APPLCORE_MESSAGES": f"SELECT message_name k, application_id ctx FROM FND_MESSAGES_B WHERE created_by<>'{SEED}'",
    "FND_MANAGE_APPLCORE_STANDARD_LOOKUPS": (f"SELECT lookup_type||'.'||lookup_code||' ('||enabled_flag||')' k, last_updated_by ctx "
                                             f"FROM FND_LOOKUP_VALUES_B WHERE last_updated_by<>'{SEED}'"),
    "FND_MANAGE_APPLICATIONS_CORE_PROFILE_OPTIONS": CUSTOM_PROFILES,
    "FND_MANAGE_APPLICATIONS_CORE_ADMINISTRATOR_PROFILE_VALUES": CUSTOM_PROFILES,
    "FND_MANAGE_APPLCORE_VALUE_SETS": f"SELECT value_set_code k, validation_type ctx FROM FND_VS_VALUE_SETS WHERE created_by<>'{SEED}'",
    "FND_MANAGE_APPLCORE_DESCRIPTIVE_FLEXFIELDS": (f"SELECT descriptive_flexfield_code||'.'||context_code||'.'||segment_code k, "
                                                   f"column_name ctx FROM FND_DF_SEGMENTS_B WHERE created_by<>'{SEED}'"),
    "FND_MANAGE_APPLICATIONS_CORE_ATTACHMENT_ENTITIES": f"SELECT entity_name k, table_name ctx FROM FND_DOCUMENT_ENTITIES WHERE created_by<>'{SEED}'",
    "FND_MANAGE_APPLICATIONS_CORE_ATTACHMENT_CATEGORIES": f"SELECT category_name k, NULL ctx FROM FND_DOCUMENT_CATEGORIES WHERE created_by<>'{SEED}'",
}


def sql_list(values):
    return ",".join("'" + v.replace("'", "''") + "'" for v in sorted(values))


def profile_sql(names):
    return ("SELECT o.profile_option_name||' ['||v.level_name||CASE WHEN v.level_name<>'SITE' THEN ':'||v.level_value END"
            "||'] = '||v.profile_option_value k, CASE WHEN v.last_updated_by='" + SEED + "' THEN 'seed' ELSE v.last_updated_by END ctx "
            "FROM FND_PROFILE_OPTION_VALUES v JOIN FND_PROFILE_OPTIONS_B o ON o.profile_option_id=v.profile_option_id "
            f"WHERE o.profile_option_name IN ({sql_list(names)})")


def lookup_sql(types):
    return ("SELECT l.lookup_type||'.'||l.lookup_code||' ('||l.enabled_flag||')' k, t.meaning ctx FROM FND_LOOKUP_VALUES_B l "
            "LEFT JOIN FND_LOOKUP_VALUES_TL t ON t.lookup_type=l.lookup_type AND t.lookup_code=l.lookup_code "
            "AND t.set_id=l.set_id AND t.view_application_id=l.view_application_id AND t.language=USERENV('LANG') "
            f"WHERE l.lookup_type IN ({sql_list(types)})")


def bu_profile_sql(names):
    return ("SELECT p.profile_option_name||' @ '||NVL((SELECT bu_name FROM FUN_ALL_BUSINESS_UNITS_V u WHERE u.bu_id=p.bu_org_id),'-')"
            "||' = '||p.profile_option_value k, p.use_site_value_flag ctx FROM SVC_BU_PROFILE_VALUES p "
            f"WHERE p.profile_option_name IN ({sql_list(names)})")


def count_sql(detail):
    return f"SELECT COUNT(*) cnt FROM (\n{detail}\n)"


def params_lookups(p):
    out = set()
    for m in re.finditer(r"(?i)(?:^|&)(?:custom)?(?:parent|child)?lookupTypes?=([^&]+)", p or ""):
        out.update(x.strip() for x in m.group(1).split(",") if x.strip())
    return out


def params_profiles(p):
    m = re.search(r"(?i)(?:^|&)profileList=([^&]+)", p or "")
    return {x.strip() for x in m.group(1).split(",") if x.strip()} if m else set()


def module_label(list_name):
    s = re.sub(r"^(Define|Maintain|Manage)\s+", "", list_name or "").strip()
    s = re.sub(r"\s+(for Service|Configuration)$", "", s)
    return s[:32]


class Fusion:
    def __init__(self, base, user, pw, report=None):
        self.base, self.user, self.pw = base, user, pw
        self.report = report or fbip.SQL_REPORT_DEFAULT

    def rows(self, sql):
        return fbip.parse_rows(fbip.run_sql(self.base, self.user, self.pw, self.report, sql))[1]


def connect(args):
    if args.fusion_bip_env:
        c = json.loads((Path.home() / ".config/fusion-bip/config.json").read_text())["environments"][args.fusion_bip_env]
        return Fusion(c["base"], c["user"], c["pass"])
    import profiles
    prof = profiles.load(args.client) or sys.exit(f"No existe el cliente '{args.client}'.")
    e = next((e for e in prof["environments"] if e["name"] == args.env), None) or sys.exit(f"Sin entorno {args.env}.")
    pw = profiles.get_password(args.client, args.env) or sys.exit(f"Sin contraseña guardada para {args.env}.")
    return Fusion(e["base"], e["user"], pw, prof.get("sql_report"))


def build(fx, project):
    ip = fx.rows("SELECT impl_project_id, task_list_id, impl_project_name FROM ASM_IMPL_PROJECTS_VL "
                 f"WHERE short_name='{project.replace(chr(39), '')}'")
    if not ip:
        sys.exit(f"No existe el implementation project {project}.")
    tl = ip[0]["TASK_LIST_ID"]
    # ord: ruta de display_sequence desde la raíz → orden jerárquico estable tras los JOIN
    tree_cte = ("WITH tree AS (SELECT LEVEL lvl, SYS_CONNECT_BY_PATH(LPAD(i.display_sequence, 6, '0'), '/') ord, i.* "
                f"FROM ASM_TASK_LIST_ITEMS i START WITH i.task_list_id={int(tl)} "
                "CONNECT BY PRIOR i.item_task_list_id=i.task_list_id AND PRIOR i.item_type_code='LIST') ")
    tree = fx.rows(tree_cte + "SELECT tree.lvl, tree.ord, tree.item_type_code typ, tree.mandatory_flag mand, "
                   "NVL(t.task_name, l.task_list_name) name, t.task_short_name short_name, "
                   "t.parameters params, t.adf_task_flow flow FROM tree "
                   "LEFT JOIN ASK_TASKS_VL t ON tree.item_type_code='TASK' AND t.task_id=tree.item_task_id "
                   "LEFT JOIN ASM_TASK_LISTS_VL l ON tree.item_type_code='LIST' AND l.task_list_id=tree.item_task_list_id "
                   "ORDER BY tree.ord")
    attrs = fx.rows(tree_cte + "SELECT t.task_short_name, v.bo_attribute_short_name attr, v.bo_attribute_value val "
                    "FROM ASK_TASKS_VL t JOIN ASK_BO_ATTRIBUTE_VALUES v ON v.task_id=t.task_id "
                    "WHERE t.task_id IN (SELECT item_task_id FROM tree WHERE item_type_code='TASK')")
    prof, look = {}, {}
    for a in attrs:
        d = prof if a["ATTR"] == "profileOptionName" else look if a["ATTR"] == "lookupType" else None
        if d is not None and a.get("VAL"):
            d.setdefault(a["TASK_SHORT_NAME"], set()).add(a["VAL"])

    items, seen, parents = [], set(), {}
    for r in tree:
        lvl = int(r["LVL"])
        if r["TYP"] == "LIST":
            parents[lvl] = r["NAME"]
            continue
        sn = r["SHORT_NAME"]
        if not sn or sn in seen:
            continue
        seen.add(sn)
        p = (r.get("PARAMS") or "") + "&" + (r.get("FLOW") or "")
        lookups = look.get(sn, set()) | params_lookups(p)
        bu_prof = params_profiles(p)
        if sn in MANUAL:
            detail, method = MANUAL[sn], "SQL"
        elif prof.get(sn):
            detail, method = profile_sql(prof[sn]), "PERFIL"
        elif lookups:
            detail, method = lookup_sql(lookups), "LOOKUP"
        elif bu_prof:
            detail, method = bu_profile_sql(bu_prof), "PERFIL BU"
        else:
            detail, method = None, "UI"
        top = parents.get(2) or parents.get(1) or ""
        items.append(OrderedDict([
            ("module", module_label(top)), ("step", len(items) + 1), ("task", r["NAME"]),
            ("responsible", ""), ("config_method", method), ("rest_resource", None),
            ("fsm_task", sn), ("task_list", parents.get(lvl - 1, "")),
            ("mandatory", r.get("MAND") == "Y"),
            ("count_sql", count_sql(detail) if detail else None), ("detail_sql", detail),
        ]))
    return ip[0], items


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--project", required=True, help="short name del implementation project")
    ap.add_argument("--client"), ap.add_argument("--env")
    ap.add_argument("--fusion-bip-env", help="entorno de ~/.config/fusion-bip/config.json")
    ap.add_argument("--name", required=True, help="nombre del checklist en la app (p. ej. Service)")
    ap.add_argument("--out", required=True)
    ap.add_argument("--validate", action="store_true", help="ejecuta cada conteo y descarta las SQL que fallan")
    args = ap.parse_args()
    fx = connect(args)
    ip, items = build(fx, args.project)
    if args.validate:
        print("Validando conteos…")
        for it in items:
            if not it["count_sql"]:
                continue
            try:
                fx.rows(it["count_sql"])
            except Exception as e:
                print(f"  ✗ {it['fsm_task']}: {(str(e).splitlines() + [''])[1][:120]} → UI")
                it.update(config_method="UI", count_sql=None, detail_sql=None)
    out = {"name": args.name, "source": {"project": args.project, "project_name": ip["IMPL_PROJECT_NAME"],
                                         "env": args.env or args.fusion_bip_env},
           "items": items}
    Path(args.out).parent.mkdir(parents=True, exist_ok=True)
    Path(args.out).write_text(json.dumps(out, indent=1, ensure_ascii=False))
    by = {}
    for it in items:
        by[it["config_method"]] = by.get(it["config_method"], 0) + 1
    print(f"{len(items)} tareas → {args.out}  ·  " + ", ".join(f"{k}: {v}" for k, v in sorted(by.items())))


if __name__ == "__main__":
    main()
