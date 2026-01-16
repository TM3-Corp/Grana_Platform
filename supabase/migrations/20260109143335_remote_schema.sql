


SET statement_timeout = 0;
SET lock_timeout = 0;
SET idle_in_transaction_session_timeout = 0;
SET client_encoding = 'UTF8';
SET standard_conforming_strings = on;
SELECT pg_catalog.set_config('search_path', '', false);
SET check_function_bodies = false;
SET xmloption = content;
SET client_min_messages = warning;
SET row_security = off;


COMMENT ON SCHEMA "public" IS 'standard public schema';



CREATE EXTENSION IF NOT EXISTS "pg_graphql" WITH SCHEMA "graphql";






CREATE EXTENSION IF NOT EXISTS "pg_stat_statements" WITH SCHEMA "extensions";






CREATE EXTENSION IF NOT EXISTS "pgcrypto" WITH SCHEMA "extensions";






CREATE EXTENSION IF NOT EXISTS "supabase_vault" WITH SCHEMA "vault";






CREATE EXTENSION IF NOT EXISTS "uuid-ossp" WITH SCHEMA "extensions";






CREATE OR REPLACE FUNCTION "public"."audit_order_changes"() RETURNS "trigger"
    LANGUAGE "plpgsql"
    AS $$
BEGIN
    -- Solo auditar si hay cambios reales
    IF (OLD.channel_id IS DISTINCT FROM NEW.channel_id) THEN
        INSERT INTO orders_audit (order_id, field_changed, old_value, new_value, changed_by, change_type)
        VALUES (NEW.id, 'channel_id', OLD.channel_id::text, NEW.channel_id::text,
                COALESCE(NEW.corrected_by, 'system'),
                CASE WHEN NEW.is_corrected THEN 'manual_correction' ELSE 'system_update' END);
    END IF;

    IF (OLD.total IS DISTINCT FROM NEW.total) THEN
        INSERT INTO orders_audit (order_id, field_changed, old_value, new_value, changed_by, change_type)
        VALUES (NEW.id, 'total', OLD.total::text, NEW.total::text,
                COALESCE(NEW.corrected_by, 'system'),
                CASE WHEN NEW.is_corrected THEN 'manual_correction' ELSE 'system_update' END);
    END IF;

    IF (OLD.customer_id IS DISTINCT FROM NEW.customer_id) THEN
        INSERT INTO orders_audit (order_id, field_changed, old_value, new_value, changed_by, change_type)
        VALUES (NEW.id, 'customer_id', OLD.customer_id::text, NEW.customer_id::text,
                COALESCE(NEW.corrected_by, 'system'),
                CASE WHEN NEW.is_corrected THEN 'manual_correction' ELSE 'system_update' END);
    END IF;

    RETURN NEW;
END;
$$;


ALTER FUNCTION "public"."audit_order_changes"() OWNER TO "postgres";


CREATE OR REPLACE FUNCTION "public"."calculate_units_per_box"("p_units_per_display" integer, "p_displays_per_box" integer) RETURNS integer
    LANGUAGE "plpgsql" IMMUTABLE
    AS $$
BEGIN
    RETURN p_units_per_display * p_displays_per_box;
END;
$$;


ALTER FUNCTION "public"."calculate_units_per_box"("p_units_per_display" integer, "p_displays_per_box" integer) OWNER TO "postgres";


CREATE OR REPLACE FUNCTION "public"."calculate_units_per_pallet"("p_units_per_display" integer, "p_displays_per_box" integer, "p_boxes_per_pallet" integer) RETURNS integer
    LANGUAGE "plpgsql" IMMUTABLE
    AS $$
BEGIN
    RETURN p_units_per_display * p_displays_per_box * p_boxes_per_pallet;
END;
$$;


ALTER FUNCTION "public"."calculate_units_per_pallet"("p_units_per_display" integer, "p_displays_per_box" integer, "p_boxes_per_pallet" integer) OWNER TO "postgres";


CREATE OR REPLACE FUNCTION "public"."update_api_credentials_updated_at"() RETURNS "trigger"
    LANGUAGE "plpgsql"
    AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$;


ALTER FUNCTION "public"."update_api_credentials_updated_at"() OWNER TO "postgres";


CREATE OR REPLACE FUNCTION "public"."update_product_catalog_updated_at"() RETURNS "trigger"
    LANGUAGE "plpgsql"
    AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$;


ALTER FUNCTION "public"."update_product_catalog_updated_at"() OWNER TO "postgres";


CREATE OR REPLACE FUNCTION "public"."update_product_stock"() RETURNS "trigger"
    LANGUAGE "plpgsql"
    AS $$
BEGIN
    -- Al crear un order_item, reducir stock
    IF (TG_OP = 'INSERT') THEN
        UPDATE products
        SET current_stock = current_stock - NEW.quantity
        WHERE id = NEW.product_id;

        -- Registrar movimiento de inventario
        INSERT INTO inventory_movements (product_id, order_id, movement_type, quantity, stock_after)
        VALUES (NEW.product_id, NEW.order_id, 'sale', -NEW.quantity,
                (SELECT current_stock FROM products WHERE id = NEW.product_id));

        -- Crear alerta si stock bajo
        INSERT INTO alerts (alert_type, severity, related_entity_type, related_entity_id, title, message)
        SELECT 'low_stock', 'warning', 'product', p.id,
               'Stock bajo: ' || p.name,
               'El producto ' || p.name || ' tiene solo ' || p.current_stock || ' unidades'
        FROM products p
        WHERE p.id = NEW.product_id AND p.current_stock < p.min_stock;
    END IF;

    RETURN NEW;
END;
$$;


ALTER FUNCTION "public"."update_product_stock"() OWNER TO "postgres";


CREATE OR REPLACE FUNCTION "public"."update_relbase_mappings_updated_at"() RETURNS "trigger"
    LANGUAGE "plpgsql"
    AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$;


ALTER FUNCTION "public"."update_relbase_mappings_updated_at"() OWNER TO "postgres";


CREATE OR REPLACE FUNCTION "public"."update_sku_mappings_updated_at"() RETURNS "trigger"
    LANGUAGE "plpgsql"
    AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$;


ALTER FUNCTION "public"."update_sku_mappings_updated_at"() OWNER TO "postgres";


CREATE OR REPLACE FUNCTION "public"."update_units_per_box"() RETURNS "trigger"
    LANGUAGE "plpgsql"
    AS $$
BEGIN
    -- Keep units_per_box in sync with hierarchy
    NEW.units_per_box := NEW.units_per_display * NEW.displays_per_box;
    RETURN NEW;
END;
$$;


ALTER FUNCTION "public"."update_units_per_box"() OWNER TO "postgres";


CREATE OR REPLACE FUNCTION "public"."update_updated_at_column"() RETURNS "trigger"
    LANGUAGE "plpgsql"
    AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$;


ALTER FUNCTION "public"."update_updated_at_column"() OWNER TO "postgres";


CREATE OR REPLACE FUNCTION "public"."update_warehouse_stock"("p_product_id" integer, "p_warehouse_id" integer, "p_quantity" integer, "p_lot_number" character varying DEFAULT NULL::character varying, "p_expiration_date" "date" DEFAULT NULL::"date", "p_updated_by" character varying DEFAULT 'system'::character varying) RETURNS "void"
    LANGUAGE "plpgsql"
    AS $$
BEGIN
    INSERT INTO warehouse_stock (
        product_id,
        warehouse_id,
        quantity,
        lot_number,
        expiration_date,
        last_updated,
        updated_by
    )
    VALUES (
        p_product_id,
        p_warehouse_id,
        p_quantity,
        p_lot_number,
        p_expiration_date,
        NOW(),
        p_updated_by
    )
    ON CONFLICT (product_id, warehouse_id, lot_number)
    DO UPDATE SET
        quantity = EXCLUDED.quantity,
        expiration_date = EXCLUDED.expiration_date,
        last_updated = NOW(),
        updated_by = EXCLUDED.updated_by;
END;
$$;


ALTER FUNCTION "public"."update_warehouse_stock"("p_product_id" integer, "p_warehouse_id" integer, "p_quantity" integer, "p_lot_number" character varying, "p_expiration_date" "date", "p_updated_by" character varying) OWNER TO "postgres";


COMMENT ON FUNCTION "public"."update_warehouse_stock"("p_product_id" integer, "p_warehouse_id" integer, "p_quantity" integer, "p_lot_number" character varying, "p_expiration_date" "date", "p_updated_by" character varying) IS 'Upsert warehouse stock with lot tracking - allows multiple lots per product/warehouse';


SET default_tablespace = '';

SET default_table_access_method = "heap";


CREATE TABLE IF NOT EXISTS "public"."alerts" (
    "id" integer NOT NULL,
    "alert_type" character varying(50) NOT NULL,
    "severity" character varying(20) NOT NULL,
    "related_entity_type" character varying(50),
    "related_entity_id" integer,
    "title" character varying(255) NOT NULL,
    "message" "text" NOT NULL,
    "is_resolved" boolean DEFAULT false,
    "resolved_at" timestamp without time zone,
    "resolved_by" character varying(100),
    "created_at" timestamp without time zone DEFAULT "now"()
);


ALTER TABLE "public"."alerts" OWNER TO "postgres";


CREATE SEQUENCE IF NOT EXISTS "public"."alerts_id_seq"
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE "public"."alerts_id_seq" OWNER TO "postgres";


ALTER SEQUENCE "public"."alerts_id_seq" OWNED BY "public"."alerts"."id";



CREATE TABLE IF NOT EXISTS "public"."api_credentials" (
    "id" integer NOT NULL,
    "service_name" character varying(50) NOT NULL,
    "access_token" "text",
    "refresh_token" "text",
    "token_expires_at" timestamp with time zone,
    "additional_data" "jsonb" DEFAULT '{}'::"jsonb",
    "created_at" timestamp with time zone DEFAULT "now"(),
    "updated_at" timestamp with time zone DEFAULT "now"()
);


ALTER TABLE "public"."api_credentials" OWNER TO "postgres";


COMMENT ON TABLE "public"."api_credentials" IS 'Stores OAuth tokens for external services (MercadoLibre, etc.) persistently';



COMMENT ON COLUMN "public"."api_credentials"."service_name" IS 'Unique identifier for the service (mercadolibre, shopify, etc.)';



COMMENT ON COLUMN "public"."api_credentials"."access_token" IS 'Current access token for API calls';



COMMENT ON COLUMN "public"."api_credentials"."refresh_token" IS 'Token used to get new access tokens';



COMMENT ON COLUMN "public"."api_credentials"."token_expires_at" IS 'When the current access token expires';



COMMENT ON COLUMN "public"."api_credentials"."additional_data" IS 'Service-specific data like seller_id, app_id, etc.';



CREATE SEQUENCE IF NOT EXISTS "public"."api_credentials_id_seq"
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE "public"."api_credentials_id_seq" OWNER TO "postgres";


ALTER SEQUENCE "public"."api_credentials_id_seq" OWNED BY "public"."api_credentials"."id";



CREATE TABLE IF NOT EXISTS "public"."api_keys" (
    "id" integer NOT NULL,
    "key_hash" character varying(255) NOT NULL,
    "name" character varying(255) NOT NULL,
    "user_id" integer,
    "permissions" "jsonb" DEFAULT '[]'::"jsonb",
    "rate_limit" integer DEFAULT 100,
    "is_active" boolean DEFAULT true,
    "last_used_at" timestamp without time zone,
    "created_at" timestamp without time zone DEFAULT "now"()
);


ALTER TABLE "public"."api_keys" OWNER TO "postgres";


COMMENT ON TABLE "public"."api_keys" IS 'API keys for external integrations and programmatic access';



COMMENT ON COLUMN "public"."api_keys"."key_hash" IS 'SHA-256 hash of the API key (never store raw key)';



COMMENT ON COLUMN "public"."api_keys"."permissions" IS 'JSON array of permission strings like ["read:orders", "write:products"]';



COMMENT ON COLUMN "public"."api_keys"."rate_limit" IS 'Maximum requests per minute for this key';



CREATE SEQUENCE IF NOT EXISTS "public"."api_keys_id_seq"
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE "public"."api_keys_id_seq" OWNER TO "postgres";


ALTER SEQUENCE "public"."api_keys_id_seq" OWNED BY "public"."api_keys"."id";



CREATE TABLE IF NOT EXISTS "public"."channel_equivalents" (
    "id" integer NOT NULL,
    "shopify_product_id" integer,
    "mercadolibre_product_id" integer,
    "equivalence_confidence" numeric(3,2),
    "verified" boolean DEFAULT false,
    "notes" "text",
    "created_at" timestamp without time zone DEFAULT "now"(),
    "updated_at" timestamp without time zone DEFAULT "now"(),
    CONSTRAINT "channel_equivalents_equivalence_confidence_check" CHECK ((("equivalence_confidence" >= (0)::numeric) AND ("equivalence_confidence" <= (1)::numeric)))
);


ALTER TABLE "public"."channel_equivalents" OWNER TO "postgres";


COMMENT ON TABLE "public"."channel_equivalents" IS 'Maps equivalent products across sales channels (Shopify ↔ MercadoLibre)';



CREATE SEQUENCE IF NOT EXISTS "public"."channel_equivalents_id_seq"
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE "public"."channel_equivalents_id_seq" OWNER TO "postgres";


ALTER SEQUENCE "public"."channel_equivalents_id_seq" OWNED BY "public"."channel_equivalents"."id";



CREATE TABLE IF NOT EXISTS "public"."channel_product_equivalents" (
    "id" integer NOT NULL,
    "channel_product_sku" character varying(100) NOT NULL,
    "official_product_sku" character varying(100) NOT NULL,
    "channel" character varying(50) NOT NULL,
    "confidence_score" numeric(3,2) DEFAULT 1.0,
    "mapping_method" character varying(50),
    "notes" "text",
    "created_at" timestamp without time zone DEFAULT CURRENT_TIMESTAMP,
    "updated_at" timestamp without time zone DEFAULT CURRENT_TIMESTAMP
);


ALTER TABLE "public"."channel_product_equivalents" OWNER TO "postgres";


COMMENT ON TABLE "public"."channel_product_equivalents" IS 'Maps channel-specific product SKUs to official catalog SKUs';



COMMENT ON COLUMN "public"."channel_product_equivalents"."confidence_score" IS 'Confidence in the mapping (1.0 = exact match, < 1.0 = fuzzy/inferred)';



COMMENT ON COLUMN "public"."channel_product_equivalents"."mapping_method" IS 'How the mapping was created (manual, exact_match, fuzzy_match, etc.)';



CREATE SEQUENCE IF NOT EXISTS "public"."channel_product_equivalents_id_seq"
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE "public"."channel_product_equivalents_id_seq" OWNER TO "postgres";


ALTER SEQUENCE "public"."channel_product_equivalents_id_seq" OWNED BY "public"."channel_product_equivalents"."id";



CREATE TABLE IF NOT EXISTS "public"."channels" (
    "id" integer NOT NULL,
    "code" character varying(50) NOT NULL,
    "name" character varying(100) NOT NULL,
    "description" "text",
    "type" character varying(50),
    "is_active" boolean DEFAULT true,
    "created_at" timestamp without time zone DEFAULT "now"(),
    "updated_at" timestamp without time zone DEFAULT "now"(),
    "external_id" character varying(255),
    "source" character varying(50)
);


ALTER TABLE "public"."channels" OWNER TO "postgres";


COMMENT ON COLUMN "public"."channels"."external_id" IS 'External ID from source system (e.g., Relbase channel_id: 3768=CORPORATIVO, 1448=ECOMMERCE, 1459=RETAIL, 3906=DISTRIBUIDOR, 1544=EMPORIOS)';



COMMENT ON COLUMN "public"."channels"."source" IS 'Source system identifier: relbase, shopify, mercadolibre, manual, etc.';



CREATE SEQUENCE IF NOT EXISTS "public"."channels_id_seq"
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE "public"."channels_id_seq" OWNER TO "postgres";


ALTER SEQUENCE "public"."channels_id_seq" OWNED BY "public"."channels"."id";



CREATE TABLE IF NOT EXISTS "public"."customer_channel_rules" (
    "id" integer NOT NULL,
    "customer_external_id" character varying(50) NOT NULL,
    "channel_external_id" integer NOT NULL,
    "channel_name" character varying(100) NOT NULL,
    "rule_reason" "text" NOT NULL,
    "priority" integer DEFAULT 1,
    "is_active" boolean DEFAULT true,
    "created_by" character varying(100),
    "created_at" timestamp without time zone DEFAULT CURRENT_TIMESTAMP,
    "updated_at" timestamp without time zone DEFAULT CURRENT_TIMESTAMP
);


ALTER TABLE "public"."customer_channel_rules" OWNER TO "postgres";


COMMENT ON TABLE "public"."customer_channel_rules" IS 'Business rules to correct customer channel assignments when RelBase data has errors or omissions';



COMMENT ON COLUMN "public"."customer_channel_rules"."customer_external_id" IS 'RelBase customer_id (external ID from API)';



COMMENT ON COLUMN "public"."customer_channel_rules"."channel_external_id" IS 'RelBase channel_id that should be used for this customer';



COMMENT ON COLUMN "public"."customer_channel_rules"."rule_reason" IS 'Business justification for why this customer belongs to this channel';



COMMENT ON COLUMN "public"."customer_channel_rules"."priority" IS 'Priority level for rule application (higher number = higher priority)';



COMMENT ON COLUMN "public"."customer_channel_rules"."is_active" IS 'Whether this rule is currently being applied';



CREATE SEQUENCE IF NOT EXISTS "public"."customer_channel_rules_id_seq"
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE "public"."customer_channel_rules_id_seq" OWNER TO "postgres";


ALTER SEQUENCE "public"."customer_channel_rules_id_seq" OWNED BY "public"."customer_channel_rules"."id";



CREATE TABLE IF NOT EXISTS "public"."customers" (
    "id" integer NOT NULL,
    "external_id" character varying(255),
    "source" character varying(50),
    "rut" character varying(20),
    "name" character varying(255) NOT NULL,
    "name_fantasy" character varying(255),
    "email" character varying(255),
    "phone" character varying(50),
    "address" "text",
    "city" character varying(100),
    "commune" character varying(100),
    "type_customer" character varying(50),
    "is_active" boolean DEFAULT true,
    "created_at" timestamp without time zone DEFAULT "now"(),
    "updated_at" timestamp without time zone DEFAULT "now"(),
    "assigned_channel_id" integer,
    "assigned_channel_name" character varying(100),
    "channel_assigned_by" character varying(100),
    "channel_assigned_at" timestamp without time zone
);


ALTER TABLE "public"."customers" OWNER TO "postgres";


COMMENT ON COLUMN "public"."customers"."assigned_channel_id" IS 'Admin-assigned channel ID. Takes priority over RelBase channel_id when displaying data.';



COMMENT ON COLUMN "public"."customers"."assigned_channel_name" IS 'Human-readable channel name for the assigned channel.';



COMMENT ON COLUMN "public"."customers"."channel_assigned_by" IS 'Who assigned this channel (admin email, migration script, etc.)';



COMMENT ON COLUMN "public"."customers"."channel_assigned_at" IS 'When the channel was assigned to this customer.';



CREATE SEQUENCE IF NOT EXISTS "public"."customers_id_seq"
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE "public"."customers_id_seq" OWNER TO "postgres";


ALTER SEQUENCE "public"."customers_id_seq" OWNED BY "public"."customers"."id";



CREATE TABLE IF NOT EXISTS "public"."dim_date" (
    "date_id" integer NOT NULL,
    "date" "date" NOT NULL,
    "year" integer NOT NULL,
    "quarter" integer NOT NULL,
    "month" integer NOT NULL,
    "week" integer NOT NULL,
    "day_of_week" integer NOT NULL,
    "day_of_month" integer NOT NULL,
    "day_of_year" integer NOT NULL,
    "month_name" character varying(20),
    "quarter_name" character varying(10),
    "year_month" character varying(7),
    "year_quarter" character varying(7),
    "week_year" character varying(8),
    "is_weekend" boolean,
    "is_holiday" boolean DEFAULT false,
    "fiscal_year" integer,
    "fiscal_quarter" integer,
    "created_at" timestamp without time zone DEFAULT "now"()
);


ALTER TABLE "public"."dim_date" OWNER TO "postgres";


COMMENT ON TABLE "public"."dim_date" IS 'Date dimension table for OLAP analytics. Provides date hierarchies for efficient time-based queries. Covers 2020-2030.';



COMMENT ON COLUMN "public"."dim_date"."date_id" IS 'Primary key in YYYYMMDD format (e.g., 20250315)';



COMMENT ON COLUMN "public"."dim_date"."is_holiday" IS 'Chilean holidays (to be populated)';



COMMENT ON COLUMN "public"."dim_date"."fiscal_year" IS 'Fiscal year (same as calendar year for Grana)';



COMMENT ON COLUMN "public"."dim_date"."fiscal_quarter" IS 'Fiscal quarter (Q1=Jan-Mar, Q2=Apr-Jun, Q3=Jul-Sep, Q4=Oct-Dec)';



CREATE TABLE IF NOT EXISTS "public"."product_variants" (
    "id" integer NOT NULL,
    "base_product_id" integer NOT NULL,
    "variant_product_id" integer NOT NULL,
    "quantity_multiplier" integer NOT NULL,
    "packaging_type" character varying(50),
    "is_active" boolean DEFAULT true,
    "created_at" timestamp without time zone DEFAULT "now"(),
    "updated_at" timestamp without time zone DEFAULT "now"(),
    CONSTRAINT "product_variants_check" CHECK (("base_product_id" <> "variant_product_id")),
    CONSTRAINT "product_variants_quantity_multiplier_check" CHECK (("quantity_multiplier" > 0))
);


ALTER TABLE "public"."product_variants" OWNER TO "postgres";


COMMENT ON TABLE "public"."product_variants" IS 'Tracks packaging relationships between products (e.g., Display 16 = 16× Individual)';



CREATE TABLE IF NOT EXISTS "public"."products" (
    "id" integer NOT NULL,
    "external_id" character varying(255),
    "source" character varying(50),
    "sku" character varying(100) NOT NULL,
    "name" character varying(255) NOT NULL,
    "description" "text",
    "category" character varying(100),
    "brand" character varying(100),
    "unit" character varying(50),
    "units_per_box" integer,
    "cost_price" numeric(12,2),
    "sale_price" numeric(12,2),
    "current_stock" integer DEFAULT 0,
    "min_stock" integer DEFAULT 10,
    "is_active" boolean DEFAULT true,
    "created_at" timestamp without time zone DEFAULT "now"(),
    "updated_at" timestamp without time zone DEFAULT "now"(),
    "units_per_display" integer DEFAULT 1,
    "displays_per_box" integer DEFAULT 1,
    "boxes_per_pallet" integer DEFAULT 1,
    "display_name" character varying(50) DEFAULT 'display'::character varying,
    "box_name" character varying(50) DEFAULT 'caja master'::character varying,
    "pallet_name" character varying(50) DEFAULT 'pallet'::character varying,
    "subfamily" character varying(200),
    "format" character varying(100),
    "package_type" character varying(50),
    "units_per_package" integer,
    "master_box_sku" character varying(50),
    "master_box_name" character varying(200),
    "items_per_master_box" integer,
    "units_per_master_box" integer,
    "recommended_min_stock" integer DEFAULT 0,
    CONSTRAINT "check_boxes_per_pallet_positive" CHECK (("boxes_per_pallet" > 0)),
    CONSTRAINT "check_displays_per_box_positive" CHECK (("displays_per_box" > 0)),
    CONSTRAINT "check_units_per_display_positive" CHECK (("units_per_display" > 0))
);


ALTER TABLE "public"."products" OWNER TO "postgres";


COMMENT ON COLUMN "public"."products"."category" IS 'Product family: GRANOLAS, BARRAS, CRACKERS, KEEPERS, KRUMS';



COMMENT ON COLUMN "public"."products"."units_per_display" IS 'Cuántas unidades individuales forman 1 display/bandeja';



COMMENT ON COLUMN "public"."products"."displays_per_box" IS 'Cuántos displays/bandejas forman 1 caja master';



COMMENT ON COLUMN "public"."products"."boxes_per_pallet" IS 'Cuántas cajas master forman 1 pallet';



COMMENT ON COLUMN "public"."products"."display_name" IS 'Nombre en español para el display (ej: "display", "bandeja", "pack")';



COMMENT ON COLUMN "public"."products"."box_name" IS 'Nombre en español para la caja (ej: "caja master", "caja", "bulto")';



COMMENT ON COLUMN "public"."products"."pallet_name" IS 'Nombre en español para el pallet (ej: "pallet", "tarima")';



COMMENT ON COLUMN "public"."products"."subfamily" IS 'Product subfamily: e.g., "Granola Low Carb Almendras", "Barra Low Carb Cacao Maní"';



COMMENT ON COLUMN "public"."products"."format" IS 'Product format: e.g., "260g", "X1", "X5", "X16", "Sachet 40g"';



COMMENT ON COLUMN "public"."products"."package_type" IS 'Package type: DISPLAY, GRANEL, DOYPACK, SACHET, BANDEJA, UNIDAD';



COMMENT ON COLUMN "public"."products"."units_per_package" IS 'Number of units in this package (e.g., 5 for X5 display)';



COMMENT ON COLUMN "public"."products"."master_box_sku" IS 'SKU of the master box containing this product';



COMMENT ON COLUMN "public"."products"."master_box_name" IS 'Name of the master box';



COMMENT ON COLUMN "public"."products"."items_per_master_box" IS 'Number of displays/packages in master box';



COMMENT ON COLUMN "public"."products"."units_per_master_box" IS 'Total number of individual units in master box';



CREATE OR REPLACE VIEW "public"."inventory_consolidated" AS
 SELECT "p_base"."id" AS "base_product_id",
    "p_base"."sku" AS "base_sku",
    "p_base"."name" AS "base_name",
    "p_base"."source" AS "base_source",
    "p_base"."sale_price" AS "base_unit_price",
    "p_base"."current_stock" AS "base_direct_stock",
    "count"(DISTINCT "pv"."variant_product_id") AS "num_variants",
    COALESCE("sum"(("p_variant"."current_stock" * "pv"."quantity_multiplier")), (0)::bigint) AS "variant_stock_as_units",
    ("p_base"."current_stock" + COALESCE("sum"(("p_variant"."current_stock" * "pv"."quantity_multiplier")), (0)::bigint)) AS "total_units_available",
        CASE
            WHEN (("p_base"."current_stock" + COALESCE("sum"(("p_variant"."current_stock" * "pv"."quantity_multiplier")), (0)::bigint)) < 0) THEN 'OVERSOLD'::"text"
            WHEN (("p_base"."current_stock" + COALESCE("sum"(("p_variant"."current_stock" * "pv"."quantity_multiplier")), (0)::bigint)) = 0) THEN 'OUT_OF_STOCK'::"text"
            WHEN (("p_base"."current_stock" + COALESCE("sum"(("p_variant"."current_stock" * "pv"."quantity_multiplier")), (0)::bigint)) < 50) THEN 'LOW_STOCK'::"text"
            ELSE 'OK'::"text"
        END AS "stock_status",
    ((("p_base"."current_stock" + COALESCE("sum"(("p_variant"."current_stock" * "pv"."quantity_multiplier")), (0)::bigint)))::numeric * "p_base"."sale_price") AS "inventory_value"
   FROM (("public"."products" "p_base"
     LEFT JOIN "public"."product_variants" "pv" ON ((("p_base"."id" = "pv"."base_product_id") AND ("pv"."is_active" = true))))
     LEFT JOIN "public"."products" "p_variant" ON (("pv"."variant_product_id" = "p_variant"."id")))
  WHERE ("p_base"."is_active" = true)
  GROUP BY "p_base"."id", "p_base"."sku", "p_base"."name", "p_base"."source", "p_base"."sale_price", "p_base"."current_stock";


ALTER VIEW "public"."inventory_consolidated" OWNER TO "postgres";


COMMENT ON VIEW "public"."inventory_consolidated" IS 'Real inventory in base units for each product family';



CREATE TABLE IF NOT EXISTS "public"."warehouse_stock" (
    "id" integer NOT NULL,
    "product_id" integer NOT NULL,
    "warehouse_id" integer NOT NULL,
    "quantity" integer DEFAULT 0 NOT NULL,
    "last_updated" timestamp without time zone DEFAULT "now"(),
    "updated_by" character varying(100),
    "lot_number" character varying(100),
    "expiration_date" "date"
);


ALTER TABLE "public"."warehouse_stock" OWNER TO "postgres";


COMMENT ON TABLE "public"."warehouse_stock" IS 'Stock quantity per product per warehouse';



COMMENT ON COLUMN "public"."warehouse_stock"."product_id" IS 'Foreign key to products table';



COMMENT ON COLUMN "public"."warehouse_stock"."warehouse_id" IS 'Foreign key to warehouses table';



COMMENT ON COLUMN "public"."warehouse_stock"."quantity" IS 'Current stock quantity (can be negative for oversold items)';



COMMENT ON COLUMN "public"."warehouse_stock"."last_updated" IS 'Timestamp of last stock update';



COMMENT ON COLUMN "public"."warehouse_stock"."updated_by" IS 'User or system that updated the stock';



COMMENT ON COLUMN "public"."warehouse_stock"."lot_number" IS 'Lot/Batch serial number from Relbase API';



COMMENT ON COLUMN "public"."warehouse_stock"."expiration_date" IS 'Expiration date of this lot';



CREATE TABLE IF NOT EXISTS "public"."warehouses" (
    "id" integer NOT NULL,
    "code" character varying(50) NOT NULL,
    "name" character varying(100) NOT NULL,
    "location" character varying(200),
    "update_method" character varying(20) NOT NULL,
    "is_active" boolean DEFAULT true,
    "created_at" timestamp without time zone DEFAULT "now"(),
    "updated_at" timestamp without time zone DEFAULT "now"(),
    "external_id" character varying(255),
    "source" character varying(50) DEFAULT 'relbase'::character varying,
    CONSTRAINT "check_warehouse_code_format" CHECK ((("code")::"text" ~ '^[a-z_]+$'::"text")),
    CONSTRAINT "warehouses_update_method_check" CHECK ((("update_method")::"text" = ANY ((ARRAY['manual_upload'::character varying, 'api'::character varying])::"text"[])))
);


ALTER TABLE "public"."warehouses" OWNER TO "postgres";


COMMENT ON TABLE "public"."warehouses" IS 'Catalog of warehouse locations (Amplifica locations, Packner, Orinoco, Mercado Libre)';



COMMENT ON COLUMN "public"."warehouses"."code" IS 'Unique identifier code for warehouse (e.g., amplifica_centro, packner)';



COMMENT ON COLUMN "public"."warehouses"."name" IS 'Human-readable name (e.g., Amplifica - Centro)';



COMMENT ON COLUMN "public"."warehouses"."update_method" IS 'How stock is updated: manual_upload (Excel) or api (automatic)';



COMMENT ON COLUMN "public"."warehouses"."external_id" IS 'External ID from source system (e.g., Relbase warehouse_id)';



COMMENT ON COLUMN "public"."warehouses"."source" IS 'Source system: relbase, manual, etc.';



COMMENT ON CONSTRAINT "check_warehouse_code_format" ON "public"."warehouses" IS 'Warehouse codes must be lowercase with underscores only';



CREATE OR REPLACE VIEW "public"."inventory_general" AS
 SELECT "p"."id",
    "p"."sku",
    "p"."name",
    "p"."category",
    "p"."subfamily",
    "max"(
        CASE
            WHEN (("w"."code")::"text" = 'amplifica_centro'::"text") THEN COALESCE("ws"."quantity", 0)
            ELSE 0
        END) AS "stock_amplifica_centro",
    "max"(
        CASE
            WHEN (("w"."code")::"text" = 'amplifica_lareina'::"text") THEN COALESCE("ws"."quantity", 0)
            ELSE 0
        END) AS "stock_amplifica_lareina",
    "max"(
        CASE
            WHEN (("w"."code")::"text" = 'amplifica_lobarnechea'::"text") THEN COALESCE("ws"."quantity", 0)
            ELSE 0
        END) AS "stock_amplifica_lobarnechea",
    "max"(
        CASE
            WHEN (("w"."code")::"text" = 'amplifica_quilicura'::"text") THEN COALESCE("ws"."quantity", 0)
            ELSE 0
        END) AS "stock_amplifica_quilicura",
    "max"(
        CASE
            WHEN (("w"."code")::"text" = 'packner'::"text") THEN COALESCE("ws"."quantity", 0)
            ELSE 0
        END) AS "stock_packner",
    "max"(
        CASE
            WHEN (("w"."code")::"text" = 'orinoco'::"text") THEN COALESCE("ws"."quantity", 0)
            ELSE 0
        END) AS "stock_orinoco",
    "max"(
        CASE
            WHEN (("w"."code")::"text" = 'mercadolibre'::"text") THEN COALESCE("ws"."quantity", 0)
            ELSE 0
        END) AS "stock_mercadolibre",
    COALESCE("sum"("ws"."quantity"), (0)::bigint) AS "stock_total",
    "max"("ws"."last_updated") AS "last_updated"
   FROM (("public"."products" "p"
     LEFT JOIN "public"."warehouse_stock" "ws" ON (("ws"."product_id" = "p"."id")))
     LEFT JOIN "public"."warehouses" "w" ON ((("w"."id" = "ws"."warehouse_id") AND ("w"."is_active" = true))))
  WHERE ("p"."is_active" = true)
  GROUP BY "p"."id", "p"."sku", "p"."name", "p"."category", "p"."subfamily"
  ORDER BY "p"."category", "p"."name";


ALTER VIEW "public"."inventory_general" OWNER TO "postgres";


COMMENT ON VIEW "public"."inventory_general" IS 'Consolidated inventory view with stock by warehouse (aggregates all lots per product)';



CREATE TABLE IF NOT EXISTS "public"."inventory_movements" (
    "id" integer NOT NULL,
    "product_id" integer,
    "order_id" integer,
    "movement_type" character varying(50) NOT NULL,
    "quantity" integer NOT NULL,
    "stock_before" integer,
    "stock_after" integer,
    "reason" "text",
    "created_by" character varying(100),
    "created_at" timestamp without time zone DEFAULT "now"()
);


ALTER TABLE "public"."inventory_movements" OWNER TO "postgres";


CREATE SEQUENCE IF NOT EXISTS "public"."inventory_movements_id_seq"
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE "public"."inventory_movements_id_seq" OWNER TO "postgres";


ALTER SEQUENCE "public"."inventory_movements_id_seq" OWNED BY "public"."inventory_movements"."id";



CREATE OR REPLACE VIEW "public"."inventory_planning_facts" AS
 WITH "stock_by_expiration" AS (
         SELECT "ws"."product_id",
            "p"."sku",
            "w"."code" AS "warehouse_code",
            "ws"."quantity",
            "ws"."lot_number",
            "ws"."expiration_date",
                CASE
                    WHEN ("ws"."expiration_date" IS NOT NULL) THEN ("ws"."expiration_date" - CURRENT_DATE)
                    ELSE NULL::integer
                END AS "days_to_expiration",
                CASE
                    WHEN ("ws"."expiration_date" IS NULL) THEN 'no_date'::"text"
                    WHEN ("ws"."expiration_date" < CURRENT_DATE) THEN 'expired'::"text"
                    WHEN ("ws"."expiration_date" <= (CURRENT_DATE + '30 days'::interval)) THEN 'expiring_soon'::"text"
                    WHEN ("ws"."expiration_date" <= (CURRENT_DATE + '60 days'::interval)) THEN 'expiring_60d'::"text"
                    ELSE 'valid'::"text"
                END AS "expiration_category"
           FROM (("public"."warehouse_stock" "ws"
             JOIN "public"."products" "p" ON ((("p"."id" = "ws"."product_id") AND ("p"."is_active" = true))))
             JOIN "public"."warehouses" "w" ON ((("w"."id" = "ws"."warehouse_id") AND ("w"."is_active" = true))))
          WHERE ("ws"."lot_number" IS NOT NULL)
        )
 SELECT "sku",
    COALESCE("sum"("quantity"), (0)::bigint) AS "stock_total",
    COALESCE("sum"(
        CASE
            WHEN ("expiration_category" = 'expired'::"text") THEN "quantity"
            ELSE 0
        END), (0)::bigint) AS "stock_expired",
    COALESCE("sum"(
        CASE
            WHEN ("expiration_category" = 'expiring_soon'::"text") THEN "quantity"
            ELSE 0
        END), (0)::bigint) AS "stock_expiring_30d",
    COALESCE("sum"(
        CASE
            WHEN ("expiration_category" = 'expiring_60d'::"text") THEN "quantity"
            ELSE 0
        END), (0)::bigint) AS "stock_expiring_60d",
    COALESCE("sum"(
        CASE
            WHEN ("expiration_category" = 'valid'::"text") THEN "quantity"
            ELSE 0
        END), (0)::bigint) AS "stock_valid",
    COALESCE("sum"(
        CASE
            WHEN ("expiration_category" = 'no_date'::"text") THEN "quantity"
            ELSE 0
        END), (0)::bigint) AS "stock_no_date",
    COALESCE("sum"(
        CASE
            WHEN ("expiration_category" = ANY (ARRAY['valid'::"text", 'no_date'::"text", 'expiring_60d'::"text"])) THEN "quantity"
            ELSE 0
        END), (0)::bigint) AS "stock_usable",
    COALESCE("sum"(
        CASE
            WHEN ("expiration_category" = 'expiring_soon'::"text") THEN "quantity"
            ELSE 0
        END), (0)::bigint) AS "stock_at_risk",
    "min"(
        CASE
            WHEN (("expiration_date" IS NOT NULL) AND ("expiration_date" > CURRENT_DATE)) THEN "expiration_date"
            ELSE NULL::"date"
        END) AS "earliest_expiration",
    "min"(
        CASE
            WHEN (("expiration_date" IS NOT NULL) AND ("expiration_date" > CURRENT_DATE)) THEN ("expiration_date" - CURRENT_DATE)
            ELSE NULL::integer
        END) AS "days_to_earliest_expiration",
    "count"(DISTINCT
        CASE
            WHEN ("expiration_category" = 'expired'::"text") THEN "lot_number"
            ELSE NULL::character varying
        END) AS "lots_expired",
    "count"(DISTINCT
        CASE
            WHEN ("expiration_category" = 'expiring_soon'::"text") THEN "lot_number"
            ELSE NULL::character varying
        END) AS "lots_expiring_soon",
    "count"(DISTINCT
        CASE
            WHEN ("expiration_category" = 'valid'::"text") THEN "lot_number"
            ELSE NULL::character varying
        END) AS "lots_valid",
    "count"(DISTINCT "lot_number") AS "lots_total"
   FROM "stock_by_expiration"
  GROUP BY "sku";


ALTER VIEW "public"."inventory_planning_facts" OWNER TO "postgres";


COMMENT ON VIEW "public"."inventory_planning_facts" IS 'Aggregated inventory by SKU with expiration-aware stock classification for production planning.
stock_usable = valid + no_date + expiring_60d (excludes expired and expiring_soon).
stock_at_risk = expiring_soon (within 30 days, may need promotion).';



CREATE TABLE IF NOT EXISTS "public"."manual_corrections" (
    "id" integer NOT NULL,
    "order_id" integer,
    "correction_type" character varying(50) NOT NULL,
    "description" "text" NOT NULL,
    "corrected_by" character varying(100) NOT NULL,
    "corrected_at" timestamp without time zone DEFAULT "now"(),
    "audit_entries" integer[]
);


ALTER TABLE "public"."manual_corrections" OWNER TO "postgres";


COMMENT ON TABLE "public"."manual_corrections" IS 'Registro de correcciones manuales realizadas por usuarios';



CREATE SEQUENCE IF NOT EXISTS "public"."manual_corrections_id_seq"
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE "public"."manual_corrections_id_seq" OWNER TO "postgres";


ALTER SEQUENCE "public"."manual_corrections_id_seq" OWNED BY "public"."manual_corrections"."id";



CREATE TABLE IF NOT EXISTS "public"."ml_tokens" (
    "id" integer NOT NULL,
    "access_token" "text" NOT NULL,
    "refresh_token" "text" NOT NULL,
    "expires_at" timestamp without time zone,
    "created_at" timestamp without time zone DEFAULT "now"(),
    "updated_at" timestamp without time zone DEFAULT "now"()
);


ALTER TABLE "public"."ml_tokens" OWNER TO "postgres";


CREATE SEQUENCE IF NOT EXISTS "public"."ml_tokens_id_seq"
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE "public"."ml_tokens_id_seq" OWNER TO "postgres";


ALTER SEQUENCE "public"."ml_tokens_id_seq" OWNED BY "public"."ml_tokens"."id";



CREATE TABLE IF NOT EXISTS "public"."order_items" (
    "id" integer NOT NULL,
    "order_id" integer,
    "product_id" integer,
    "product_sku" character varying(100),
    "product_name" character varying(255),
    "quantity" integer NOT NULL,
    "unit_price" numeric(12,2) NOT NULL,
    "subtotal" numeric(12,2) NOT NULL,
    "tax_amount" numeric(12,2),
    "total" numeric(12,2) NOT NULL,
    "created_at" timestamp without time zone DEFAULT "now"(),
    "sku_primario" character varying(100)
);


ALTER TABLE "public"."order_items" OWNER TO "postgres";


COMMENT ON COLUMN "public"."order_items"."sku_primario" IS 'Mapped primary SKU code from CSV (Codigos_Grana_Ingles.csv).
Handles legacy codes like ANU-BAKC_U04010 → BAKC_U04010.
This field is populated by the audit.py mapping logic and enables
efficient OLAP grouping by SKU Primario.';



CREATE SEQUENCE IF NOT EXISTS "public"."order_items_id_seq"
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE "public"."order_items_id_seq" OWNER TO "postgres";


ALTER SEQUENCE "public"."order_items_id_seq" OWNED BY "public"."order_items"."id";



CREATE TABLE IF NOT EXISTS "public"."orders" (
    "id" integer NOT NULL,
    "external_id" character varying(255),
    "order_number" character varying(100) NOT NULL,
    "source" character varying(50) NOT NULL,
    "customer_id" integer,
    "channel_id" integer,
    "subtotal" numeric(12,2),
    "tax_amount" numeric(12,2),
    "shipping_cost" numeric(12,2),
    "discount_amount" numeric(12,2),
    "total" numeric(12,2) NOT NULL,
    "status" character varying(50) DEFAULT 'pending'::character varying,
    "payment_status" character varying(50),
    "fulfillment_status" character varying(50),
    "order_date" timestamp without time zone NOT NULL,
    "payment_date" timestamp without time zone,
    "shipped_date" timestamp without time zone,
    "delivered_date" timestamp without time zone,
    "invoice_number" character varying(100),
    "invoice_type" character varying(50),
    "invoice_date" timestamp without time zone,
    "invoice_status" character varying(50),
    "is_corrected" boolean DEFAULT false,
    "correction_reason" "text",
    "corrected_by" character varying(100),
    "corrected_at" timestamp without time zone,
    "customer_notes" "text",
    "internal_notes" "text",
    "created_at" timestamp without time zone DEFAULT "now"(),
    "updated_at" timestamp without time zone DEFAULT "now"()
);


ALTER TABLE "public"."orders" OWNER TO "postgres";


COMMENT ON TABLE "public"."orders" IS 'Tabla principal de pedidos - Single Source of Truth editable y auditable';



COMMENT ON COLUMN "public"."orders"."is_corrected" IS 'Indica si el pedido fue editado manualmente por Macarena o equipo';



COMMENT ON COLUMN "public"."orders"."correction_reason" IS 'Razón por la cual se corrigió manualmente el pedido';



CREATE TABLE IF NOT EXISTS "public"."orders_audit" (
    "id" integer NOT NULL,
    "order_id" integer,
    "field_changed" character varying(100) NOT NULL,
    "old_value" "text",
    "new_value" "text",
    "changed_by" character varying(100) NOT NULL,
    "changed_at" timestamp without time zone DEFAULT "now"(),
    "reason" "text",
    "change_type" character varying(50),
    "ip_address" character varying(50),
    "user_agent" "text"
);


ALTER TABLE "public"."orders_audit" OWNER TO "postgres";


COMMENT ON TABLE "public"."orders_audit" IS 'Auditoría completa de todos los cambios en pedidos - CRÍTICO para Macarena';



CREATE SEQUENCE IF NOT EXISTS "public"."orders_audit_id_seq"
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE "public"."orders_audit_id_seq" OWNER TO "postgres";


ALTER SEQUENCE "public"."orders_audit_id_seq" OWNED BY "public"."orders_audit"."id";



CREATE SEQUENCE IF NOT EXISTS "public"."orders_id_seq"
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE "public"."orders_id_seq" OWNER TO "postgres";


ALTER SEQUENCE "public"."orders_id_seq" OWNED BY "public"."orders"."id";



CREATE TABLE IF NOT EXISTS "public"."product_catalog" (
    "id" bigint NOT NULL,
    "sku" character varying(100) NOT NULL,
    "sku_master" character varying(100),
    "category" character varying(100),
    "brand" character varying(100),
    "language" character varying(50),
    "product_name" "text" NOT NULL,
    "master_box_name" "text",
    "package_type" character varying(100),
    "units_per_display" integer,
    "units_per_master_box" integer,
    "items_per_master_box" integer,
    "is_master_sku" boolean DEFAULT false,
    "base_code" character varying(50),
    "is_active" boolean DEFAULT true,
    "created_at" timestamp with time zone DEFAULT "now"(),
    "updated_at" timestamp with time zone DEFAULT "now"(),
    "peso_film" numeric(10,4),
    "peso_display_total" numeric(10,4),
    "peso_caja_master_total" numeric(10,4),
    "peso_etiqueta_total" numeric(10,4),
    "sku_value" numeric(12,2),
    "sku_master_value" numeric(12,2),
    "sku_primario" character varying(50),
    "is_inventory_active" boolean DEFAULT true
);


ALTER TABLE "public"."product_catalog" OWNER TO "postgres";


COMMENT ON TABLE "public"."product_catalog" IS 'Product catalog imported from Codigos_Grana_Ingles.csv - replaces CSV dependency';



COMMENT ON COLUMN "public"."product_catalog"."sku" IS 'Primary SKU identifier (e.g., GRAL_U26010)';



COMMENT ON COLUMN "public"."product_catalog"."sku_master" IS 'Master box SKU if this product has one (e.g., GRAL_C01010)';



COMMENT ON COLUMN "public"."product_catalog"."category" IS 'Product category: GRANOLAS, BARRAS, CRACKERS, KEEPERS, KRUMS, GALLETAS';



COMMENT ON COLUMN "public"."product_catalog"."units_per_display" IS 'Conversion factor for normal SKUs (UNIDADES POR DISPLAY)';



COMMENT ON COLUMN "public"."product_catalog"."units_per_master_box" IS 'Units per master box (unidades x CM)';



COMMENT ON COLUMN "public"."product_catalog"."items_per_master_box" IS 'Items per master box (Items por CM)';



COMMENT ON COLUMN "public"."product_catalog"."base_code" IS 'Base product code extracted from SKU (e.g., GRAL from GRAL_U26010)';



COMMENT ON COLUMN "public"."product_catalog"."is_inventory_active" IS 'When FALSE, this SKU is hidden from Inventario General view.
Used for discontinued products or SKUs we do not want to track in inventory.
Default TRUE - all products show by default.';



CREATE SEQUENCE IF NOT EXISTS "public"."product_catalog_id_seq"
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE "public"."product_catalog_id_seq" OWNER TO "postgres";


ALTER SEQUENCE "public"."product_catalog_id_seq" OWNED BY "public"."product_catalog"."id";



CREATE OR REPLACE VIEW "public"."product_families" AS
 SELECT "p_base"."id" AS "base_product_id",
    "p_base"."sku" AS "base_sku",
    "p_base"."name" AS "base_name",
    "p_variant"."id" AS "variant_product_id",
    "p_variant"."sku" AS "variant_sku",
    "p_variant"."name" AS "variant_name",
    "pv"."quantity_multiplier",
    "pv"."packaging_type",
    "p_variant"."current_stock" AS "variant_stock",
    ("p_variant"."current_stock" * "pv"."quantity_multiplier") AS "variant_stock_as_base_units",
    "p_variant"."sale_price" AS "variant_price",
    "p_base"."sale_price" AS "base_unit_price",
    "round"(("p_variant"."sale_price" / ("pv"."quantity_multiplier")::numeric), 2) AS "variant_unit_price",
        CASE
            WHEN ("round"(("p_variant"."sale_price" / ("pv"."quantity_multiplier")::numeric), 2) < "p_base"."sale_price") THEN "round"(((("p_base"."sale_price" - ("p_variant"."sale_price" / ("pv"."quantity_multiplier")::numeric)) / "p_base"."sale_price") * (100)::numeric), 1)
            ELSE (0)::numeric
        END AS "discount_percentage"
   FROM (("public"."products" "p_base"
     JOIN "public"."product_variants" "pv" ON ((("p_base"."id" = "pv"."base_product_id") AND ("pv"."is_active" = true))))
     JOIN "public"."products" "p_variant" ON (("pv"."variant_product_id" = "p_variant"."id")))
  WHERE ("p_base"."is_active" = true);


ALTER VIEW "public"."product_families" OWNER TO "postgres";


COMMENT ON VIEW "public"."product_families" IS 'Complete product families showing all packaging variants';



CREATE TABLE IF NOT EXISTS "public"."product_inventory_settings" (
    "id" integer NOT NULL,
    "sku" character varying(100) NOT NULL,
    "estimation_months" integer DEFAULT 6 NOT NULL,
    "safety_buffer_pct" numeric(5,4) DEFAULT 0.20 NOT NULL,
    "lead_time_days" integer DEFAULT 7 NOT NULL,
    "planning_notes" "text",
    "created_at" timestamp without time zone DEFAULT "now"(),
    "updated_at" timestamp without time zone DEFAULT "now"(),
    CONSTRAINT "product_inventory_settings_estimation_months_check" CHECK (("estimation_months" = ANY (ARRAY[1, 3, 6])))
);


ALTER TABLE "public"."product_inventory_settings" OWNER TO "postgres";


COMMENT ON TABLE "public"."product_inventory_settings" IS 'Per-product inventory planning preferences';



COMMENT ON COLUMN "public"."product_inventory_settings"."estimation_months" IS 'Sales averaging period: 1, 3, or 6 months';



COMMENT ON COLUMN "public"."product_inventory_settings"."safety_buffer_pct" IS 'Safety stock as percentage above projected demand (0.20 = 20%)';



COMMENT ON COLUMN "public"."product_inventory_settings"."lead_time_days" IS 'Production/restock lead time in days';



CREATE SEQUENCE IF NOT EXISTS "public"."product_inventory_settings_id_seq"
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE "public"."product_inventory_settings_id_seq" OWNER TO "postgres";


ALTER SEQUENCE "public"."product_inventory_settings_id_seq" OWNED BY "public"."product_inventory_settings"."id";



CREATE SEQUENCE IF NOT EXISTS "public"."product_variants_id_seq"
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE "public"."product_variants_id_seq" OWNER TO "postgres";


ALTER SEQUENCE "public"."product_variants_id_seq" OWNED BY "public"."product_variants"."id";



CREATE SEQUENCE IF NOT EXISTS "public"."products_id_seq"
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE "public"."products_id_seq" OWNER TO "postgres";


ALTER SEQUENCE "public"."products_id_seq" OWNED BY "public"."products"."id";



CREATE TABLE IF NOT EXISTS "public"."relbase_product_mappings" (
    "id" integer NOT NULL,
    "relbase_code" character varying(100) NOT NULL,
    "relbase_name" character varying(500),
    "official_sku" character varying(100),
    "product_id" integer,
    "match_type" character varying(50) NOT NULL,
    "confidence_level" character varying(20) NOT NULL,
    "mapping_notes" "text",
    "total_sales" integer DEFAULT 0,
    "first_seen_date" timestamp without time zone,
    "last_seen_date" timestamp without time zone,
    "inferred_category" character varying(100),
    "inferred_variant" character varying(100),
    "is_service_item" boolean DEFAULT false,
    "is_legacy_code" boolean DEFAULT false,
    "needs_manual_review" boolean DEFAULT false,
    "created_at" timestamp without time zone DEFAULT "now"(),
    "updated_at" timestamp without time zone DEFAULT "now"(),
    "description" "text",
    "product_id_relbase" integer,
    "url_image" "text"
);


ALTER TABLE "public"."relbase_product_mappings" OWNER TO "postgres";


COMMENT ON TABLE "public"."relbase_product_mappings" IS 'Maps Relbase product codes to official Grana catalog SKUs';



COMMENT ON COLUMN "public"."relbase_product_mappings"."relbase_code" IS 'Product code from Relbase system (e.g., BAKC_U20010, ANU-3322808180)';



COMMENT ON COLUMN "public"."relbase_product_mappings"."official_sku" IS 'Mapped SKU from official Grana catalog';



COMMENT ON COLUMN "public"."relbase_product_mappings"."match_type" IS 'Mapping strategy: exact, pack_variant, caja_master, caja_fuzzy, no_match';



COMMENT ON COLUMN "public"."relbase_product_mappings"."confidence_level" IS 'Mapping confidence: high, medium, low, none';



COMMENT ON COLUMN "public"."relbase_product_mappings"."is_service_item" IS 'True for shipping fees, price adjustments, etc. (not actual products)';



COMMENT ON COLUMN "public"."relbase_product_mappings"."is_legacy_code" IS 'True for auto-generated ANU- codes from system migrations';



COMMENT ON COLUMN "public"."relbase_product_mappings"."description" IS 'Detailed product description from Relbase API - critical for parsing ANU- code package information';



COMMENT ON COLUMN "public"."relbase_product_mappings"."product_id_relbase" IS 'Relbase internal product ID - stable identifier that does not change even if code changes';



COMMENT ON COLUMN "public"."relbase_product_mappings"."url_image" IS 'Product image URL from Relbase - useful for visual confirmation during manual mapping';



CREATE SEQUENCE IF NOT EXISTS "public"."relbase_product_mappings_id_seq"
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE "public"."relbase_product_mappings_id_seq" OWNER TO "postgres";


ALTER SEQUENCE "public"."relbase_product_mappings_id_seq" OWNED BY "public"."relbase_product_mappings"."id";



CREATE TABLE IF NOT EXISTS "public"."sku_mappings" (
    "id" integer NOT NULL,
    "source_pattern" character varying(255) NOT NULL,
    "pattern_type" character varying(20) NOT NULL,
    "source_filter" character varying(50),
    "target_sku" character varying(100) NOT NULL,
    "quantity_multiplier" integer DEFAULT 1,
    "rule_name" character varying(100),
    "confidence" integer DEFAULT 100,
    "priority" integer DEFAULT 50,
    "is_active" boolean DEFAULT true,
    "created_at" timestamp with time zone DEFAULT "now"(),
    "updated_at" timestamp with time zone DEFAULT "now"(),
    "created_by" character varying(100),
    "notes" "text",
    CONSTRAINT "chk_confidence" CHECK ((("confidence" >= 0) AND ("confidence" <= 100))),
    CONSTRAINT "chk_pattern_type" CHECK ((("pattern_type")::"text" = ANY ((ARRAY['exact'::character varying, 'prefix'::character varying, 'suffix'::character varying, 'regex'::character varying, 'contains'::character varying])::"text"[]))),
    CONSTRAINT "chk_priority" CHECK ((("priority" >= 0) AND ("priority" <= 100))),
    CONSTRAINT "chk_quantity_multiplier" CHECK (("quantity_multiplier" > 0))
);


ALTER TABLE "public"."sku_mappings" OWNER TO "postgres";


COMMENT ON TABLE "public"."sku_mappings" IS 'Database-driven SKU mapping rules to replace hardcoded logic in audit.py';



COMMENT ON COLUMN "public"."sku_mappings"."source_pattern" IS 'Raw SKU pattern to match (exact value or pattern based on pattern_type)';



COMMENT ON COLUMN "public"."sku_mappings"."pattern_type" IS 'How to interpret source_pattern: exact=literal match, prefix=startswith, suffix=endswith, regex=regular expression, contains=substring';



COMMENT ON COLUMN "public"."sku_mappings"."source_filter" IS 'Optional: only apply rule for specific data source (relbase, mercadolibre, shopify)';



COMMENT ON COLUMN "public"."sku_mappings"."target_sku" IS 'Official SKU from product_catalog that this maps to';



COMMENT ON COLUMN "public"."sku_mappings"."quantity_multiplier" IS 'Multiply order quantity by this factor (for PACK mappings)';



COMMENT ON COLUMN "public"."sku_mappings"."confidence" IS 'Confidence score for the mapping (0-100%)';



COMMENT ON COLUMN "public"."sku_mappings"."priority" IS 'Higher priority rules are checked first (0-100)';



CREATE MATERIALIZED VIEW "public"."sales_facts_mv" AS
 SELECT ("to_char"("o"."order_date", 'YYYYMMDD'::"text"))::integer AS "date_id",
    "o"."order_date",
    "o"."channel_id",
    "o"."customer_id",
    "o"."source",
    "oi"."product_sku" AS "original_sku",
    COALESCE("pc_direct"."sku", "pc_master"."sku", "pc_mapped"."sku", "pc_mapped_master"."sku") AS "catalog_sku",
    COALESCE("pc_direct"."sku_primario", "pc_master"."sku_primario", "pc_mapped"."sku_primario", "pc_mapped_master"."sku_primario") AS "sku_primario",
    COALESCE("pc_direct"."product_name", "pc_master"."master_box_name", "pc_mapped"."product_name", "pc_mapped_master"."master_box_name", ("oi"."product_name")::"text") AS "product_name",
    COALESCE("pc_direct"."category", "pc_master"."category", "pc_mapped"."category", "pc_mapped_master"."category") AS "category",
    COALESCE("pc_direct"."package_type", "pc_master"."package_type", "pc_mapped"."package_type", "pc_mapped_master"."package_type") AS "package_type",
    COALESCE("pc_direct"."brand", "pc_master"."brand", "pc_mapped"."brand", "pc_mapped_master"."brand") AS "brand",
    COALESCE("pc_direct"."language", "pc_master"."language", "pc_mapped"."language", "pc_mapped_master"."language") AS "language",
    COALESCE("pc_direct"."units_per_display", "pc_mapped"."units_per_display", "pc_mapped_master"."units_per_display", 1) AS "units_per_display",
    COALESCE("pc_master"."items_per_master_box", "pc_mapped_master"."items_per_master_box", "pc_direct"."items_per_master_box", "pc_mapped"."items_per_master_box") AS "items_per_master_box",
        CASE
            WHEN ("pc_master"."sku" IS NOT NULL) THEN true
            WHEN ("pc_mapped_master"."sku" IS NOT NULL) THEN true
            ELSE false
        END AS "is_caja_master",
        CASE
            WHEN ("pc_direct"."sku" IS NOT NULL) THEN 'direct'::"text"
            WHEN ("pc_master"."sku" IS NOT NULL) THEN 'caja_master'::"text"
            WHEN ("pc_mapped"."sku" IS NOT NULL) THEN 'sku_mapping'::"text"
            WHEN ("pc_mapped_master"."sku" IS NOT NULL) THEN 'sku_mapping_caja_master'::"text"
            ELSE 'unmapped'::"text"
        END AS "match_type",
    "sm"."rule_name" AS "mapping_rule",
    COALESCE("sm"."quantity_multiplier", 1) AS "quantity_multiplier",
    "ch"."name" AS "channel_name",
    "c"."name" AS "customer_name",
    "c"."rut" AS "customer_rut",
    "oi"."quantity" AS "original_units_sold",
    ("oi"."quantity" * COALESCE("sm"."quantity_multiplier", 1)) AS "units_sold",
    "oi"."subtotal" AS "revenue",
    "oi"."unit_price",
    "oi"."total",
    "oi"."tax_amount",
    "o"."id" AS "order_id",
    "o"."external_id" AS "order_external_id",
    "o"."invoice_status",
    "o"."payment_status",
    "o"."status" AS "order_status",
    "o"."created_at" AS "order_created_at"
   FROM (((((((("public"."orders" "o"
     JOIN "public"."order_items" "oi" ON (("o"."id" = "oi"."order_id")))
     LEFT JOIN "public"."product_catalog" "pc_direct" ON (((("pc_direct"."sku")::"text" = "upper"(("oi"."product_sku")::"text")) AND ("pc_direct"."is_active" = true))))
     LEFT JOIN "public"."product_catalog" "pc_master" ON (((("pc_master"."sku_master")::"text" = "upper"(("oi"."product_sku")::"text")) AND ("pc_master"."is_active" = true) AND ("pc_direct"."sku" IS NULL))))
     LEFT JOIN "public"."sku_mappings" "sm" ON (((("sm"."source_pattern")::"text" = "upper"(("oi"."product_sku")::"text")) AND (("sm"."pattern_type")::"text" = 'exact'::"text") AND ("sm"."is_active" = true) AND ("pc_direct"."sku" IS NULL) AND ("pc_master"."sku" IS NULL))))
     LEFT JOIN "public"."product_catalog" "pc_mapped" ON (((("pc_mapped"."sku")::"text" = ("sm"."target_sku")::"text") AND ("pc_mapped"."is_active" = true))))
     LEFT JOIN "public"."product_catalog" "pc_mapped_master" ON (((("pc_mapped_master"."sku_master")::"text" = ("sm"."target_sku")::"text") AND ("pc_mapped_master"."is_active" = true) AND ("pc_mapped"."sku" IS NULL))))
     LEFT JOIN "public"."channels" "ch" ON (("o"."channel_id" = "ch"."id")))
     LEFT JOIN "public"."customers" "c" ON (("o"."customer_id" = "c"."id")))
  WHERE ((("o"."invoice_status")::"text" = ANY ((ARRAY['accepted'::character varying, 'accepted_objection'::character varying])::"text"[])) AND (("o"."status")::"text" <> 'cancelled'::"text"))
  WITH NO DATA;


ALTER MATERIALIZED VIEW "public"."sales_facts_mv" OWNER TO "postgres";


COMMENT ON MATERIALIZED VIEW "public"."sales_facts_mv" IS 'Pre-aggregated sales facts for OLAP analytics.
FIXED (Migration 025): CAJA MASTER products now inherit their base product category.
- Previously: category = ''CAJA MASTER'' (excluded from BARRAS/CRACKERS filters)
- Now: category = actual category from product_catalog (e.g., BARRAS)
- is_caja_master flag preserved for filtering CAJA MASTER specifically

SKU matching uses 4-path logic:
1. Direct match on product_catalog.sku → product_name
2. Match on product_catalog.sku_master → master_box_name (CAJA MASTER)
3a. Via sku_mappings → product_catalog.sku → mapped product data
3b. Via sku_mappings → product_catalog.sku_master → master_box_name (CAJA MASTER via ANU-/WEB)
4. No match → fallback to order_items (unmapped)

Refresh hourly or after data sync: REFRESH MATERIALIZED VIEW sales_facts_mv;';



CREATE SEQUENCE IF NOT EXISTS "public"."sku_mappings_id_seq"
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE "public"."sku_mappings_id_seq" OWNER TO "postgres";


ALTER SEQUENCE "public"."sku_mappings_id_seq" OWNED BY "public"."sku_mappings"."id";



CREATE TABLE IF NOT EXISTS "public"."sync_logs" (
    "id" integer NOT NULL,
    "source" character varying(50) NOT NULL,
    "sync_type" character varying(50) NOT NULL,
    "status" character varying(50) NOT NULL,
    "records_processed" integer DEFAULT 0,
    "records_failed" integer DEFAULT 0,
    "error_message" "text",
    "details" "jsonb",
    "started_at" timestamp without time zone DEFAULT "now"(),
    "completed_at" timestamp without time zone,
    "duration_seconds" integer
);


ALTER TABLE "public"."sync_logs" OWNER TO "postgres";


CREATE SEQUENCE IF NOT EXISTS "public"."sync_logs_id_seq"
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE "public"."sync_logs_id_seq" OWNER TO "postgres";


ALTER SEQUENCE "public"."sync_logs_id_seq" OWNED BY "public"."sync_logs"."id";



CREATE TABLE IF NOT EXISTS "public"."users" (
    "id" integer NOT NULL,
    "email" character varying(255) NOT NULL,
    "password_hash" character varying(255) NOT NULL,
    "name" character varying(255),
    "role" character varying(50) DEFAULT 'user'::character varying,
    "is_active" boolean DEFAULT true,
    "created_at" timestamp without time zone DEFAULT "now"(),
    "updated_at" timestamp without time zone DEFAULT "now"()
);


ALTER TABLE "public"."users" OWNER TO "postgres";


CREATE SEQUENCE IF NOT EXISTS "public"."users_id_seq"
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE "public"."users_id_seq" OWNER TO "postgres";


ALTER SEQUENCE "public"."users_id_seq" OWNED BY "public"."users"."id";



CREATE OR REPLACE VIEW "public"."v_low_stock_products" AS
 SELECT "id",
    "sku",
    "name",
    "current_stock",
    "min_stock",
    "category",
    ("min_stock" - "current_stock") AS "units_needed"
   FROM "public"."products" "p"
  WHERE (("current_stock" < "min_stock") AND ("is_active" = true))
  ORDER BY ("min_stock" - "current_stock") DESC;


ALTER VIEW "public"."v_low_stock_products" OWNER TO "postgres";


CREATE OR REPLACE VIEW "public"."v_orders_full" AS
 SELECT "o"."id",
    "o"."order_number",
    "o"."source",
    "o"."order_date",
    "o"."total",
    "o"."status",
    "o"."is_corrected",
    "c"."name" AS "customer_name",
    "c"."rut" AS "customer_rut",
    "ch"."name" AS "channel_name",
    "ch"."type" AS "channel_type",
    "o"."invoice_number",
    "o"."invoice_status",
    "o"."created_at",
    "o"."updated_at"
   FROM (("public"."orders" "o"
     LEFT JOIN "public"."customers" "c" ON (("o"."customer_id" = "c"."id")))
     LEFT JOIN "public"."channels" "ch" ON (("o"."channel_id" = "ch"."id")));


ALTER VIEW "public"."v_orders_full" OWNER TO "postgres";


CREATE OR REPLACE VIEW "public"."v_product_conversion" AS
 SELECT "id",
    "sku",
    "name",
    "category",
    "unit" AS "unit_name",
    "display_name",
    "box_name",
    "pallet_name",
    "units_per_display",
    "displays_per_box",
    "boxes_per_pallet",
    ("units_per_display" * "displays_per_box") AS "units_per_box",
    (("units_per_display" * "displays_per_box") * "boxes_per_pallet") AS "units_per_pallet",
    (1.0 / ("units_per_display")::numeric) AS "boxes_per_unit",
    (1.0 / (("units_per_display" * "displays_per_box"))::numeric) AS "pallets_per_unit",
    "current_stock" AS "stock_units",
    "round"((("current_stock")::numeric / (("units_per_display" * "displays_per_box"))::numeric), 2) AS "stock_boxes",
    "round"((("current_stock")::numeric / ((("units_per_display" * "displays_per_box") * "boxes_per_pallet"))::numeric), 2) AS "stock_pallets",
    "is_active",
    "created_at",
    "updated_at"
   FROM "public"."products" "p"
  WHERE ("is_active" = true);


ALTER VIEW "public"."v_product_conversion" OWNER TO "postgres";


COMMENT ON VIEW "public"."v_product_conversion" IS 'Vista completa de conversiones por producto con todos los cálculos pre-hechos';



CREATE OR REPLACE VIEW "public"."v_sales_by_channel" AS
 SELECT "ch"."code" AS "channel_code",
    "ch"."name" AS "channel_name",
    "ch"."type" AS "channel_type",
    "count"("o"."id") AS "total_orders",
    "sum"("o"."total") AS "total_sales",
    "avg"("o"."total") AS "avg_order_value",
    "min"("o"."order_date") AS "first_order",
    "max"("o"."order_date") AS "last_order"
   FROM ("public"."orders" "o"
     JOIN "public"."channels" "ch" ON (("o"."channel_id" = "ch"."id")))
  WHERE (("o"."status")::"text" <> 'cancelled'::"text")
  GROUP BY "ch"."code", "ch"."name", "ch"."type";


ALTER VIEW "public"."v_sales_by_channel" OWNER TO "postgres";


CREATE OR REPLACE VIEW "public"."warehouse_stock_by_lot" AS
 SELECT "ws"."id",
    "p"."sku",
    "p"."name" AS "product_name",
    "p"."category",
    "w"."code" AS "warehouse_code",
    "w"."name" AS "warehouse_name",
    "ws"."quantity",
    "ws"."lot_number",
    "ws"."expiration_date",
    "ws"."last_updated",
    "ws"."updated_by",
        CASE
            WHEN ("ws"."expiration_date" IS NOT NULL) THEN ("ws"."expiration_date" - CURRENT_DATE)
            ELSE NULL::integer
        END AS "days_to_expiration",
        CASE
            WHEN ("ws"."expiration_date" IS NULL) THEN 'No Date'::"text"
            WHEN ("ws"."expiration_date" < CURRENT_DATE) THEN 'Expired'::"text"
            WHEN ("ws"."expiration_date" <= (CURRENT_DATE + '30 days'::interval)) THEN 'Expiring Soon'::"text"
            ELSE 'Valid'::"text"
        END AS "expiration_status"
   FROM (("public"."warehouse_stock" "ws"
     JOIN "public"."products" "p" ON (("p"."id" = "ws"."product_id")))
     JOIN "public"."warehouses" "w" ON (("w"."id" = "ws"."warehouse_id")))
  WHERE (("p"."is_active" = true) AND ("w"."is_active" = true) AND ("ws"."lot_number" IS NOT NULL))
  ORDER BY "w"."name", "p"."category", "p"."name", "ws"."expiration_date";


ALTER VIEW "public"."warehouse_stock_by_lot" OWNER TO "postgres";


COMMENT ON VIEW "public"."warehouse_stock_by_lot" IS 'Detailed view of warehouse stock at lot level with expiration tracking.
Excludes legacy rows with NULL lot_number (pre-migration 016 data).';



CREATE SEQUENCE IF NOT EXISTS "public"."warehouse_stock_id_seq"
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE "public"."warehouse_stock_id_seq" OWNER TO "postgres";


ALTER SEQUENCE "public"."warehouse_stock_id_seq" OWNED BY "public"."warehouse_stock"."id";



CREATE SEQUENCE IF NOT EXISTS "public"."warehouses_id_seq"
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE "public"."warehouses_id_seq" OWNER TO "postgres";


ALTER SEQUENCE "public"."warehouses_id_seq" OWNED BY "public"."warehouses"."id";



ALTER TABLE ONLY "public"."alerts" ALTER COLUMN "id" SET DEFAULT "nextval"('"public"."alerts_id_seq"'::"regclass");



ALTER TABLE ONLY "public"."api_credentials" ALTER COLUMN "id" SET DEFAULT "nextval"('"public"."api_credentials_id_seq"'::"regclass");



ALTER TABLE ONLY "public"."api_keys" ALTER COLUMN "id" SET DEFAULT "nextval"('"public"."api_keys_id_seq"'::"regclass");



ALTER TABLE ONLY "public"."channel_equivalents" ALTER COLUMN "id" SET DEFAULT "nextval"('"public"."channel_equivalents_id_seq"'::"regclass");



ALTER TABLE ONLY "public"."channel_product_equivalents" ALTER COLUMN "id" SET DEFAULT "nextval"('"public"."channel_product_equivalents_id_seq"'::"regclass");



ALTER TABLE ONLY "public"."channels" ALTER COLUMN "id" SET DEFAULT "nextval"('"public"."channels_id_seq"'::"regclass");



ALTER TABLE ONLY "public"."customer_channel_rules" ALTER COLUMN "id" SET DEFAULT "nextval"('"public"."customer_channel_rules_id_seq"'::"regclass");



ALTER TABLE ONLY "public"."customers" ALTER COLUMN "id" SET DEFAULT "nextval"('"public"."customers_id_seq"'::"regclass");



ALTER TABLE ONLY "public"."inventory_movements" ALTER COLUMN "id" SET DEFAULT "nextval"('"public"."inventory_movements_id_seq"'::"regclass");



ALTER TABLE ONLY "public"."manual_corrections" ALTER COLUMN "id" SET DEFAULT "nextval"('"public"."manual_corrections_id_seq"'::"regclass");



ALTER TABLE ONLY "public"."ml_tokens" ALTER COLUMN "id" SET DEFAULT "nextval"('"public"."ml_tokens_id_seq"'::"regclass");



ALTER TABLE ONLY "public"."order_items" ALTER COLUMN "id" SET DEFAULT "nextval"('"public"."order_items_id_seq"'::"regclass");



ALTER TABLE ONLY "public"."orders" ALTER COLUMN "id" SET DEFAULT "nextval"('"public"."orders_id_seq"'::"regclass");



ALTER TABLE ONLY "public"."orders_audit" ALTER COLUMN "id" SET DEFAULT "nextval"('"public"."orders_audit_id_seq"'::"regclass");



ALTER TABLE ONLY "public"."product_catalog" ALTER COLUMN "id" SET DEFAULT "nextval"('"public"."product_catalog_id_seq"'::"regclass");



ALTER TABLE ONLY "public"."product_inventory_settings" ALTER COLUMN "id" SET DEFAULT "nextval"('"public"."product_inventory_settings_id_seq"'::"regclass");



ALTER TABLE ONLY "public"."product_variants" ALTER COLUMN "id" SET DEFAULT "nextval"('"public"."product_variants_id_seq"'::"regclass");



ALTER TABLE ONLY "public"."products" ALTER COLUMN "id" SET DEFAULT "nextval"('"public"."products_id_seq"'::"regclass");



ALTER TABLE ONLY "public"."relbase_product_mappings" ALTER COLUMN "id" SET DEFAULT "nextval"('"public"."relbase_product_mappings_id_seq"'::"regclass");



ALTER TABLE ONLY "public"."sku_mappings" ALTER COLUMN "id" SET DEFAULT "nextval"('"public"."sku_mappings_id_seq"'::"regclass");



ALTER TABLE ONLY "public"."sync_logs" ALTER COLUMN "id" SET DEFAULT "nextval"('"public"."sync_logs_id_seq"'::"regclass");



ALTER TABLE ONLY "public"."users" ALTER COLUMN "id" SET DEFAULT "nextval"('"public"."users_id_seq"'::"regclass");



ALTER TABLE ONLY "public"."warehouse_stock" ALTER COLUMN "id" SET DEFAULT "nextval"('"public"."warehouse_stock_id_seq"'::"regclass");



ALTER TABLE ONLY "public"."warehouses" ALTER COLUMN "id" SET DEFAULT "nextval"('"public"."warehouses_id_seq"'::"regclass");



ALTER TABLE ONLY "public"."alerts"
    ADD CONSTRAINT "alerts_pkey" PRIMARY KEY ("id");



ALTER TABLE ONLY "public"."api_credentials"
    ADD CONSTRAINT "api_credentials_pkey" PRIMARY KEY ("id");



ALTER TABLE ONLY "public"."api_credentials"
    ADD CONSTRAINT "api_credentials_service_name_key" UNIQUE ("service_name");



ALTER TABLE ONLY "public"."api_keys"
    ADD CONSTRAINT "api_keys_key_hash_unique" UNIQUE ("key_hash");



ALTER TABLE ONLY "public"."api_keys"
    ADD CONSTRAINT "api_keys_pkey" PRIMARY KEY ("id");



ALTER TABLE ONLY "public"."channel_equivalents"
    ADD CONSTRAINT "channel_equivalents_pkey" PRIMARY KEY ("id");



ALTER TABLE ONLY "public"."channel_equivalents"
    ADD CONSTRAINT "channel_equivalents_shopify_product_id_mercadolibre_product_key" UNIQUE ("shopify_product_id", "mercadolibre_product_id");



ALTER TABLE ONLY "public"."channel_product_equivalents"
    ADD CONSTRAINT "channel_product_equivalents_pkey" PRIMARY KEY ("id");



ALTER TABLE ONLY "public"."channels"
    ADD CONSTRAINT "channels_code_key" UNIQUE ("code");



ALTER TABLE ONLY "public"."channels"
    ADD CONSTRAINT "channels_external_source_unique" UNIQUE ("external_id", "source");



ALTER TABLE ONLY "public"."channels"
    ADD CONSTRAINT "channels_pkey" PRIMARY KEY ("id");



ALTER TABLE ONLY "public"."customer_channel_rules"
    ADD CONSTRAINT "customer_channel_rules_pkey" PRIMARY KEY ("id");



ALTER TABLE ONLY "public"."customers"
    ADD CONSTRAINT "customers_external_source_unique" UNIQUE ("external_id", "source");



ALTER TABLE ONLY "public"."customers"
    ADD CONSTRAINT "customers_pkey" PRIMARY KEY ("id");



ALTER TABLE ONLY "public"."dim_date"
    ADD CONSTRAINT "dim_date_date_key" UNIQUE ("date");



ALTER TABLE ONLY "public"."dim_date"
    ADD CONSTRAINT "dim_date_pkey" PRIMARY KEY ("date_id");



ALTER TABLE ONLY "public"."inventory_movements"
    ADD CONSTRAINT "inventory_movements_pkey" PRIMARY KEY ("id");



ALTER TABLE ONLY "public"."manual_corrections"
    ADD CONSTRAINT "manual_corrections_pkey" PRIMARY KEY ("id");



ALTER TABLE ONLY "public"."ml_tokens"
    ADD CONSTRAINT "ml_tokens_pkey" PRIMARY KEY ("id");



ALTER TABLE ONLY "public"."order_items"
    ADD CONSTRAINT "order_items_pkey" PRIMARY KEY ("id");



ALTER TABLE ONLY "public"."orders_audit"
    ADD CONSTRAINT "orders_audit_pkey" PRIMARY KEY ("id");



ALTER TABLE ONLY "public"."orders"
    ADD CONSTRAINT "orders_external_source_unique" UNIQUE ("external_id", "source");



ALTER TABLE ONLY "public"."orders"
    ADD CONSTRAINT "orders_pkey" PRIMARY KEY ("id");



ALTER TABLE ONLY "public"."product_catalog"
    ADD CONSTRAINT "product_catalog_pkey" PRIMARY KEY ("id");



ALTER TABLE ONLY "public"."product_catalog"
    ADD CONSTRAINT "product_catalog_sku_key" UNIQUE ("sku");



ALTER TABLE ONLY "public"."product_inventory_settings"
    ADD CONSTRAINT "product_inventory_settings_pkey" PRIMARY KEY ("id");



ALTER TABLE ONLY "public"."product_inventory_settings"
    ADD CONSTRAINT "product_inventory_settings_sku_key" UNIQUE ("sku");



ALTER TABLE ONLY "public"."product_variants"
    ADD CONSTRAINT "product_variants_base_product_id_variant_product_id_key" UNIQUE ("base_product_id", "variant_product_id");



ALTER TABLE ONLY "public"."product_variants"
    ADD CONSTRAINT "product_variants_pkey" PRIMARY KEY ("id");



ALTER TABLE ONLY "public"."products"
    ADD CONSTRAINT "products_pkey" PRIMARY KEY ("id");



ALTER TABLE ONLY "public"."products"
    ADD CONSTRAINT "products_sku_key" UNIQUE ("sku");



ALTER TABLE ONLY "public"."relbase_product_mappings"
    ADD CONSTRAINT "relbase_product_mappings_pkey" PRIMARY KEY ("id");



ALTER TABLE ONLY "public"."relbase_product_mappings"
    ADD CONSTRAINT "relbase_product_mappings_relbase_code_key" UNIQUE ("relbase_code");



ALTER TABLE ONLY "public"."sku_mappings"
    ADD CONSTRAINT "sku_mappings_pkey" PRIMARY KEY ("id");



ALTER TABLE ONLY "public"."sync_logs"
    ADD CONSTRAINT "sync_logs_pkey" PRIMARY KEY ("id");



ALTER TABLE ONLY "public"."channel_product_equivalents"
    ADD CONSTRAINT "unique_channel_product" UNIQUE ("channel_product_sku", "channel");



ALTER TABLE ONLY "public"."users"
    ADD CONSTRAINT "users_email_key" UNIQUE ("email");



ALTER TABLE ONLY "public"."users"
    ADD CONSTRAINT "users_pkey" PRIMARY KEY ("id");



ALTER TABLE ONLY "public"."warehouse_stock"
    ADD CONSTRAINT "warehouse_stock_pkey" PRIMARY KEY ("id");



ALTER TABLE ONLY "public"."warehouse_stock"
    ADD CONSTRAINT "warehouse_stock_product_warehouse_lot_unique" UNIQUE ("product_id", "warehouse_id", "lot_number");



COMMENT ON CONSTRAINT "warehouse_stock_product_warehouse_lot_unique" ON "public"."warehouse_stock" IS 'Allows multiple lots of same product in same warehouse, each lot identified by lot_number';



ALTER TABLE ONLY "public"."warehouses"
    ADD CONSTRAINT "warehouses_code_key" UNIQUE ("code");



ALTER TABLE ONLY "public"."warehouses"
    ADD CONSTRAINT "warehouses_pkey" PRIMARY KEY ("id");



CREATE INDEX "idx_alerts_is_resolved" ON "public"."alerts" USING "btree" ("is_resolved");



CREATE INDEX "idx_alerts_severity" ON "public"."alerts" USING "btree" ("severity");



CREATE INDEX "idx_alerts_type" ON "public"."alerts" USING "btree" ("alert_type");



CREATE INDEX "idx_api_credentials_service" ON "public"."api_credentials" USING "btree" ("service_name");



CREATE INDEX "idx_api_keys_is_active" ON "public"."api_keys" USING "btree" ("is_active");



CREATE INDEX "idx_api_keys_key_hash" ON "public"."api_keys" USING "btree" ("key_hash");



CREATE INDEX "idx_api_keys_user_id" ON "public"."api_keys" USING "btree" ("user_id");



CREATE INDEX "idx_channel" ON "public"."channel_product_equivalents" USING "btree" ("channel");



CREATE INDEX "idx_channel_equiv_ml" ON "public"."channel_equivalents" USING "btree" ("mercadolibre_product_id");



CREATE INDEX "idx_channel_equiv_shopify" ON "public"."channel_equivalents" USING "btree" ("shopify_product_id");



CREATE INDEX "idx_channel_external_id" ON "public"."customer_channel_rules" USING "btree" ("channel_external_id");



CREATE INDEX "idx_channel_product_lookup" ON "public"."channel_product_equivalents" USING "btree" ("channel", "channel_product_sku");



CREATE INDEX "idx_channel_product_sku" ON "public"."channel_product_equivalents" USING "btree" ("channel_product_sku");



CREATE INDEX "idx_channels_external_id" ON "public"."channels" USING "btree" ("external_id");



CREATE INDEX "idx_channels_external_source" ON "public"."channels" USING "btree" ("external_id", "source");



CREATE INDEX "idx_channels_source" ON "public"."channels" USING "btree" ("source");



CREATE INDEX "idx_customer_active_lookup" ON "public"."customer_channel_rules" USING "btree" ("customer_external_id", "is_active");



CREATE INDEX "idx_customer_external_id" ON "public"."customer_channel_rules" USING "btree" ("customer_external_id");



CREATE INDEX "idx_customers_assigned_channel" ON "public"."customers" USING "btree" ("assigned_channel_id") WHERE ("assigned_channel_id" IS NOT NULL);



CREATE INDEX "idx_customers_name" ON "public"."customers" USING "btree" ("name");



CREATE INDEX "idx_customers_rut" ON "public"."customers" USING "btree" ("rut");



CREATE INDEX "idx_customers_source" ON "public"."customers" USING "btree" ("source");



CREATE INDEX "idx_date_date" ON "public"."dim_date" USING "btree" ("date");



CREATE INDEX "idx_date_dow" ON "public"."dim_date" USING "btree" ("day_of_week");



CREATE INDEX "idx_date_fiscal" ON "public"."dim_date" USING "btree" ("fiscal_year", "fiscal_quarter");



CREATE INDEX "idx_date_week" ON "public"."dim_date" USING "btree" ("year", "week");



CREATE INDEX "idx_date_year_month" ON "public"."dim_date" USING "btree" ("year", "month");



CREATE INDEX "idx_date_year_quarter" ON "public"."dim_date" USING "btree" ("year", "quarter");



CREATE INDEX "idx_inventory_movements_product" ON "public"."inventory_movements" USING "btree" ("product_id");



CREATE INDEX "idx_inventory_movements_type" ON "public"."inventory_movements" USING "btree" ("movement_type");



CREATE INDEX "idx_is_active" ON "public"."customer_channel_rules" USING "btree" ("is_active");



CREATE INDEX "idx_manual_corrections_date" ON "public"."manual_corrections" USING "btree" ("corrected_at");



CREATE INDEX "idx_manual_corrections_order" ON "public"."manual_corrections" USING "btree" ("order_id");



CREATE INDEX "idx_official_product_sku" ON "public"."channel_product_equivalents" USING "btree" ("official_product_sku");



CREATE INDEX "idx_order_items_order" ON "public"."order_items" USING "btree" ("order_id");



CREATE INDEX "idx_order_items_product" ON "public"."order_items" USING "btree" ("product_id");



CREATE INDEX "idx_order_items_sku_primario" ON "public"."order_items" USING "btree" ("sku_primario");



CREATE INDEX "idx_orders_audit_changed_at" ON "public"."orders_audit" USING "btree" ("changed_at");



CREATE INDEX "idx_orders_audit_changed_by" ON "public"."orders_audit" USING "btree" ("changed_by");



CREATE INDEX "idx_orders_audit_order" ON "public"."orders_audit" USING "btree" ("order_id");



CREATE INDEX "idx_orders_channel" ON "public"."orders" USING "btree" ("channel_id");



CREATE INDEX "idx_orders_customer" ON "public"."orders" USING "btree" ("customer_id");



CREATE INDEX "idx_orders_is_corrected" ON "public"."orders" USING "btree" ("is_corrected");



CREATE INDEX "idx_orders_order_date" ON "public"."orders" USING "btree" ("order_date");



CREATE INDEX "idx_orders_order_number" ON "public"."orders" USING "btree" ("order_number");



CREATE INDEX "idx_orders_source" ON "public"."orders" USING "btree" ("source");



CREATE INDEX "idx_orders_status" ON "public"."orders" USING "btree" ("status");



CREATE INDEX "idx_product_catalog_base_code" ON "public"."product_catalog" USING "btree" ("base_code") WHERE ("is_active" = true);



CREATE INDEX "idx_product_catalog_category" ON "public"."product_catalog" USING "btree" ("category") WHERE ("is_active" = true);



CREATE INDEX "idx_product_catalog_category_active" ON "public"."product_catalog" USING "btree" ("category", "is_active");



CREATE INDEX "idx_product_catalog_is_inventory_active" ON "public"."product_catalog" USING "btree" ("is_inventory_active") WHERE ("is_inventory_active" = true);



CREATE INDEX "idx_product_catalog_product_name_gin" ON "public"."product_catalog" USING "gin" ("to_tsvector"('"spanish"'::"regconfig", "product_name"));



CREATE INDEX "idx_product_catalog_sku_master" ON "public"."product_catalog" USING "btree" ("sku_master") WHERE ("sku_master" IS NOT NULL);



CREATE INDEX "idx_product_catalog_sku_primario" ON "public"."product_catalog" USING "btree" ("sku_primario");



CREATE INDEX "idx_product_inv_settings_sku" ON "public"."product_inventory_settings" USING "btree" ("sku");



CREATE INDEX "idx_product_variants_base" ON "public"."product_variants" USING "btree" ("base_product_id");



CREATE INDEX "idx_product_variants_variant" ON "public"."product_variants" USING "btree" ("variant_product_id");



CREATE INDEX "idx_products_category" ON "public"."products" USING "btree" ("category");



CREATE INDEX "idx_products_conversion" ON "public"."products" USING "btree" ("sku", "units_per_display", "displays_per_box");



CREATE INDEX "idx_products_format" ON "public"."products" USING "btree" ("format");



CREATE INDEX "idx_products_master_box_sku" ON "public"."products" USING "btree" ("master_box_sku");



CREATE INDEX "idx_products_sku" ON "public"."products" USING "btree" ("sku");



CREATE INDEX "idx_products_source" ON "public"."products" USING "btree" ("source");



CREATE INDEX "idx_products_subfamily" ON "public"."products" USING "btree" ("subfamily");



CREATE INDEX "idx_relbase_mappings_code" ON "public"."relbase_product_mappings" USING "btree" ("relbase_code");



CREATE INDEX "idx_relbase_mappings_is_service" ON "public"."relbase_product_mappings" USING "btree" ("is_service_item") WHERE ("is_service_item" = true);



CREATE INDEX "idx_relbase_mappings_match_type" ON "public"."relbase_product_mappings" USING "btree" ("match_type");



CREATE INDEX "idx_relbase_mappings_needs_review" ON "public"."relbase_product_mappings" USING "btree" ("needs_manual_review") WHERE ("needs_manual_review" = true);



CREATE INDEX "idx_relbase_mappings_product_id" ON "public"."relbase_product_mappings" USING "btree" ("product_id");



CREATE INDEX "idx_relbase_mappings_product_id_relbase" ON "public"."relbase_product_mappings" USING "btree" ("product_id_relbase");



CREATE INDEX "idx_relbase_mappings_sku" ON "public"."relbase_product_mappings" USING "btree" ("official_sku");



CREATE INDEX "idx_sales_mv_category" ON "public"."sales_facts_mv" USING "btree" ("category");



CREATE INDEX "idx_sales_mv_channel_id" ON "public"."sales_facts_mv" USING "btree" ("channel_id");



CREATE INDEX "idx_sales_mv_customer_id" ON "public"."sales_facts_mv" USING "btree" ("customer_id");



CREATE INDEX "idx_sales_mv_date_brin" ON "public"."sales_facts_mv" USING "brin" ("order_date");



CREATE INDEX "idx_sales_mv_date_id" ON "public"."sales_facts_mv" USING "btree" ("date_id");



CREATE INDEX "idx_sales_mv_date_source" ON "public"."sales_facts_mv" USING "btree" ("date_id", "source");



CREATE INDEX "idx_sales_mv_date_source_category" ON "public"."sales_facts_mv" USING "btree" ("date_id", "source", "category") INCLUDE ("revenue", "units_sold");



CREATE INDEX "idx_sales_mv_date_source_channel" ON "public"."sales_facts_mv" USING "btree" ("date_id", "source", "channel_id") INCLUDE ("revenue", "units_sold");



CREATE INDEX "idx_sales_mv_is_caja_master" ON "public"."sales_facts_mv" USING "btree" ("is_caja_master");



CREATE INDEX "idx_sales_mv_match_type" ON "public"."sales_facts_mv" USING "btree" ("match_type");



CREATE INDEX "idx_sales_mv_order_date" ON "public"."sales_facts_mv" USING "btree" ("order_date");



CREATE INDEX "idx_sales_mv_package_type" ON "public"."sales_facts_mv" USING "btree" ("package_type");



CREATE INDEX "idx_sales_mv_revenue_desc" ON "public"."sales_facts_mv" USING "btree" ("revenue" DESC);



CREATE INDEX "idx_sales_mv_sku_primario" ON "public"."sales_facts_mv" USING "btree" ("sku_primario");



CREATE INDEX "idx_sales_mv_source" ON "public"."sales_facts_mv" USING "btree" ("source");



CREATE INDEX "idx_sku_mappings_active" ON "public"."sku_mappings" USING "btree" ("is_active") WHERE ("is_active" = true);



CREATE INDEX "idx_sku_mappings_pattern" ON "public"."sku_mappings" USING "btree" ("source_pattern");



CREATE INDEX "idx_sku_mappings_priority" ON "public"."sku_mappings" USING "btree" ("priority" DESC);



CREATE INDEX "idx_sku_mappings_source" ON "public"."sku_mappings" USING "btree" ("source_filter") WHERE ("source_filter" IS NOT NULL);



CREATE INDEX "idx_sku_mappings_target" ON "public"."sku_mappings" USING "btree" ("target_sku");



CREATE UNIQUE INDEX "idx_sku_mappings_unique_exact" ON "public"."sku_mappings" USING "btree" ("source_pattern", "source_filter") WHERE ((("pattern_type")::"text" = 'exact'::"text") AND ("is_active" = true));



CREATE INDEX "idx_sync_logs_source" ON "public"."sync_logs" USING "btree" ("source");



CREATE INDEX "idx_sync_logs_started_at" ON "public"."sync_logs" USING "btree" ("started_at");



CREATE INDEX "idx_users_email" ON "public"."users" USING "btree" ("email");



CREATE INDEX "idx_warehouse_stock_composite" ON "public"."warehouse_stock" USING "btree" ("product_id", "warehouse_id");



CREATE INDEX "idx_warehouse_stock_expiration" ON "public"."warehouse_stock" USING "btree" ("expiration_date");



CREATE INDEX "idx_warehouse_stock_lot_number" ON "public"."warehouse_stock" USING "btree" ("lot_number");



CREATE INDEX "idx_warehouse_stock_product" ON "public"."warehouse_stock" USING "btree" ("product_id");



CREATE INDEX "idx_warehouse_stock_quantity" ON "public"."warehouse_stock" USING "btree" ("quantity");



CREATE INDEX "idx_warehouse_stock_warehouse" ON "public"."warehouse_stock" USING "btree" ("warehouse_id");



CREATE INDEX "idx_warehouses_code" ON "public"."warehouses" USING "btree" ("code");



CREATE INDEX "idx_warehouses_external_id" ON "public"."warehouses" USING "btree" ("external_id");



CREATE UNIQUE INDEX "idx_warehouses_external_source" ON "public"."warehouses" USING "btree" ("external_id", "source") WHERE ("external_id" IS NOT NULL);



CREATE INDEX "idx_warehouses_is_active" ON "public"."warehouses" USING "btree" ("is_active");



CREATE UNIQUE INDEX "unique_active_customer_rule" ON "public"."customer_channel_rules" USING "btree" ("customer_external_id", "priority") WHERE ("is_active" = true);



CREATE OR REPLACE TRIGGER "audit_order_changes_trigger" AFTER UPDATE ON "public"."orders" FOR EACH ROW EXECUTE FUNCTION "public"."audit_order_changes"();



CREATE OR REPLACE TRIGGER "trigger_api_credentials_updated_at" BEFORE UPDATE ON "public"."api_credentials" FOR EACH ROW EXECUTE FUNCTION "public"."update_api_credentials_updated_at"();



CREATE OR REPLACE TRIGGER "trigger_update_product_catalog_updated_at" BEFORE UPDATE ON "public"."product_catalog" FOR EACH ROW EXECUTE FUNCTION "public"."update_product_catalog_updated_at"();



CREATE OR REPLACE TRIGGER "trigger_update_relbase_mappings_updated_at" BEFORE UPDATE ON "public"."relbase_product_mappings" FOR EACH ROW EXECUTE FUNCTION "public"."update_relbase_mappings_updated_at"();



CREATE OR REPLACE TRIGGER "trigger_update_sku_mappings_updated_at" BEFORE UPDATE ON "public"."sku_mappings" FOR EACH ROW EXECUTE FUNCTION "public"."update_sku_mappings_updated_at"();



CREATE OR REPLACE TRIGGER "trigger_update_units_per_box" BEFORE INSERT OR UPDATE ON "public"."products" FOR EACH ROW EXECUTE FUNCTION "public"."update_units_per_box"();



CREATE OR REPLACE TRIGGER "update_customers_updated_at" BEFORE UPDATE ON "public"."customers" FOR EACH ROW EXECUTE FUNCTION "public"."update_updated_at_column"();



CREATE OR REPLACE TRIGGER "update_orders_updated_at" BEFORE UPDATE ON "public"."orders" FOR EACH ROW EXECUTE FUNCTION "public"."update_updated_at_column"();



CREATE OR REPLACE TRIGGER "update_product_stock_trigger" AFTER INSERT ON "public"."order_items" FOR EACH ROW EXECUTE FUNCTION "public"."update_product_stock"();



CREATE OR REPLACE TRIGGER "update_products_updated_at" BEFORE UPDATE ON "public"."products" FOR EACH ROW EXECUTE FUNCTION "public"."update_updated_at_column"();



ALTER TABLE ONLY "public"."api_keys"
    ADD CONSTRAINT "api_keys_user_id_fkey" FOREIGN KEY ("user_id") REFERENCES "public"."users"("id");



ALTER TABLE ONLY "public"."channel_equivalents"
    ADD CONSTRAINT "channel_equivalents_mercadolibre_product_id_fkey" FOREIGN KEY ("mercadolibre_product_id") REFERENCES "public"."products"("id") ON DELETE CASCADE;



ALTER TABLE ONLY "public"."channel_equivalents"
    ADD CONSTRAINT "channel_equivalents_shopify_product_id_fkey" FOREIGN KEY ("shopify_product_id") REFERENCES "public"."products"("id") ON DELETE CASCADE;



ALTER TABLE ONLY "public"."channel_product_equivalents"
    ADD CONSTRAINT "fk_official_product" FOREIGN KEY ("official_product_sku") REFERENCES "public"."products"("sku") ON DELETE CASCADE;



ALTER TABLE ONLY "public"."inventory_movements"
    ADD CONSTRAINT "inventory_movements_order_id_fkey" FOREIGN KEY ("order_id") REFERENCES "public"."orders"("id");



ALTER TABLE ONLY "public"."inventory_movements"
    ADD CONSTRAINT "inventory_movements_product_id_fkey" FOREIGN KEY ("product_id") REFERENCES "public"."products"("id");



ALTER TABLE ONLY "public"."manual_corrections"
    ADD CONSTRAINT "manual_corrections_order_id_fkey" FOREIGN KEY ("order_id") REFERENCES "public"."orders"("id");



ALTER TABLE ONLY "public"."order_items"
    ADD CONSTRAINT "order_items_order_id_fkey" FOREIGN KEY ("order_id") REFERENCES "public"."orders"("id") ON DELETE CASCADE;



ALTER TABLE ONLY "public"."order_items"
    ADD CONSTRAINT "order_items_product_id_fkey" FOREIGN KEY ("product_id") REFERENCES "public"."products"("id");



ALTER TABLE ONLY "public"."orders_audit"
    ADD CONSTRAINT "orders_audit_order_id_fkey" FOREIGN KEY ("order_id") REFERENCES "public"."orders"("id") ON DELETE CASCADE;



ALTER TABLE ONLY "public"."orders"
    ADD CONSTRAINT "orders_channel_id_fkey" FOREIGN KEY ("channel_id") REFERENCES "public"."channels"("id");



ALTER TABLE ONLY "public"."orders"
    ADD CONSTRAINT "orders_customer_id_fkey" FOREIGN KEY ("customer_id") REFERENCES "public"."customers"("id");



ALTER TABLE ONLY "public"."product_variants"
    ADD CONSTRAINT "product_variants_base_product_id_fkey" FOREIGN KEY ("base_product_id") REFERENCES "public"."products"("id") ON DELETE CASCADE;



ALTER TABLE ONLY "public"."product_variants"
    ADD CONSTRAINT "product_variants_variant_product_id_fkey" FOREIGN KEY ("variant_product_id") REFERENCES "public"."products"("id") ON DELETE CASCADE;



ALTER TABLE ONLY "public"."relbase_product_mappings"
    ADD CONSTRAINT "relbase_product_mappings_product_id_fkey" FOREIGN KEY ("product_id") REFERENCES "public"."products"("id") ON DELETE SET NULL;



ALTER TABLE ONLY "public"."warehouse_stock"
    ADD CONSTRAINT "warehouse_stock_product_id_fkey" FOREIGN KEY ("product_id") REFERENCES "public"."products"("id") ON DELETE CASCADE;



ALTER TABLE ONLY "public"."warehouse_stock"
    ADD CONSTRAINT "warehouse_stock_warehouse_id_fkey" FOREIGN KEY ("warehouse_id") REFERENCES "public"."warehouses"("id") ON DELETE CASCADE;





ALTER PUBLICATION "supabase_realtime" OWNER TO "postgres";


GRANT USAGE ON SCHEMA "public" TO "postgres";
GRANT USAGE ON SCHEMA "public" TO "anon";
GRANT USAGE ON SCHEMA "public" TO "authenticated";
GRANT USAGE ON SCHEMA "public" TO "service_role";

























































































































































GRANT ALL ON FUNCTION "public"."audit_order_changes"() TO "anon";
GRANT ALL ON FUNCTION "public"."audit_order_changes"() TO "authenticated";
GRANT ALL ON FUNCTION "public"."audit_order_changes"() TO "service_role";



GRANT ALL ON FUNCTION "public"."calculate_units_per_box"("p_units_per_display" integer, "p_displays_per_box" integer) TO "anon";
GRANT ALL ON FUNCTION "public"."calculate_units_per_box"("p_units_per_display" integer, "p_displays_per_box" integer) TO "authenticated";
GRANT ALL ON FUNCTION "public"."calculate_units_per_box"("p_units_per_display" integer, "p_displays_per_box" integer) TO "service_role";



GRANT ALL ON FUNCTION "public"."calculate_units_per_pallet"("p_units_per_display" integer, "p_displays_per_box" integer, "p_boxes_per_pallet" integer) TO "anon";
GRANT ALL ON FUNCTION "public"."calculate_units_per_pallet"("p_units_per_display" integer, "p_displays_per_box" integer, "p_boxes_per_pallet" integer) TO "authenticated";
GRANT ALL ON FUNCTION "public"."calculate_units_per_pallet"("p_units_per_display" integer, "p_displays_per_box" integer, "p_boxes_per_pallet" integer) TO "service_role";



GRANT ALL ON FUNCTION "public"."update_api_credentials_updated_at"() TO "anon";
GRANT ALL ON FUNCTION "public"."update_api_credentials_updated_at"() TO "authenticated";
GRANT ALL ON FUNCTION "public"."update_api_credentials_updated_at"() TO "service_role";



GRANT ALL ON FUNCTION "public"."update_product_catalog_updated_at"() TO "anon";
GRANT ALL ON FUNCTION "public"."update_product_catalog_updated_at"() TO "authenticated";
GRANT ALL ON FUNCTION "public"."update_product_catalog_updated_at"() TO "service_role";



GRANT ALL ON FUNCTION "public"."update_product_stock"() TO "anon";
GRANT ALL ON FUNCTION "public"."update_product_stock"() TO "authenticated";
GRANT ALL ON FUNCTION "public"."update_product_stock"() TO "service_role";



GRANT ALL ON FUNCTION "public"."update_relbase_mappings_updated_at"() TO "anon";
GRANT ALL ON FUNCTION "public"."update_relbase_mappings_updated_at"() TO "authenticated";
GRANT ALL ON FUNCTION "public"."update_relbase_mappings_updated_at"() TO "service_role";



GRANT ALL ON FUNCTION "public"."update_sku_mappings_updated_at"() TO "anon";
GRANT ALL ON FUNCTION "public"."update_sku_mappings_updated_at"() TO "authenticated";
GRANT ALL ON FUNCTION "public"."update_sku_mappings_updated_at"() TO "service_role";



GRANT ALL ON FUNCTION "public"."update_units_per_box"() TO "anon";
GRANT ALL ON FUNCTION "public"."update_units_per_box"() TO "authenticated";
GRANT ALL ON FUNCTION "public"."update_units_per_box"() TO "service_role";



GRANT ALL ON FUNCTION "public"."update_updated_at_column"() TO "anon";
GRANT ALL ON FUNCTION "public"."update_updated_at_column"() TO "authenticated";
GRANT ALL ON FUNCTION "public"."update_updated_at_column"() TO "service_role";



GRANT ALL ON FUNCTION "public"."update_warehouse_stock"("p_product_id" integer, "p_warehouse_id" integer, "p_quantity" integer, "p_lot_number" character varying, "p_expiration_date" "date", "p_updated_by" character varying) TO "anon";
GRANT ALL ON FUNCTION "public"."update_warehouse_stock"("p_product_id" integer, "p_warehouse_id" integer, "p_quantity" integer, "p_lot_number" character varying, "p_expiration_date" "date", "p_updated_by" character varying) TO "authenticated";
GRANT ALL ON FUNCTION "public"."update_warehouse_stock"("p_product_id" integer, "p_warehouse_id" integer, "p_quantity" integer, "p_lot_number" character varying, "p_expiration_date" "date", "p_updated_by" character varying) TO "service_role";


















GRANT ALL ON TABLE "public"."alerts" TO "anon";
GRANT ALL ON TABLE "public"."alerts" TO "authenticated";
GRANT ALL ON TABLE "public"."alerts" TO "service_role";



GRANT ALL ON SEQUENCE "public"."alerts_id_seq" TO "anon";
GRANT ALL ON SEQUENCE "public"."alerts_id_seq" TO "authenticated";
GRANT ALL ON SEQUENCE "public"."alerts_id_seq" TO "service_role";



GRANT ALL ON TABLE "public"."api_credentials" TO "anon";
GRANT ALL ON TABLE "public"."api_credentials" TO "authenticated";
GRANT ALL ON TABLE "public"."api_credentials" TO "service_role";



GRANT ALL ON SEQUENCE "public"."api_credentials_id_seq" TO "anon";
GRANT ALL ON SEQUENCE "public"."api_credentials_id_seq" TO "authenticated";
GRANT ALL ON SEQUENCE "public"."api_credentials_id_seq" TO "service_role";



GRANT ALL ON TABLE "public"."api_keys" TO "anon";
GRANT ALL ON TABLE "public"."api_keys" TO "authenticated";
GRANT ALL ON TABLE "public"."api_keys" TO "service_role";



GRANT ALL ON SEQUENCE "public"."api_keys_id_seq" TO "anon";
GRANT ALL ON SEQUENCE "public"."api_keys_id_seq" TO "authenticated";
GRANT ALL ON SEQUENCE "public"."api_keys_id_seq" TO "service_role";



GRANT ALL ON TABLE "public"."channel_equivalents" TO "anon";
GRANT ALL ON TABLE "public"."channel_equivalents" TO "authenticated";
GRANT ALL ON TABLE "public"."channel_equivalents" TO "service_role";



GRANT ALL ON SEQUENCE "public"."channel_equivalents_id_seq" TO "anon";
GRANT ALL ON SEQUENCE "public"."channel_equivalents_id_seq" TO "authenticated";
GRANT ALL ON SEQUENCE "public"."channel_equivalents_id_seq" TO "service_role";



GRANT ALL ON TABLE "public"."channel_product_equivalents" TO "anon";
GRANT ALL ON TABLE "public"."channel_product_equivalents" TO "authenticated";
GRANT ALL ON TABLE "public"."channel_product_equivalents" TO "service_role";



GRANT ALL ON SEQUENCE "public"."channel_product_equivalents_id_seq" TO "anon";
GRANT ALL ON SEQUENCE "public"."channel_product_equivalents_id_seq" TO "authenticated";
GRANT ALL ON SEQUENCE "public"."channel_product_equivalents_id_seq" TO "service_role";



GRANT ALL ON TABLE "public"."channels" TO "anon";
GRANT ALL ON TABLE "public"."channels" TO "authenticated";
GRANT ALL ON TABLE "public"."channels" TO "service_role";



GRANT ALL ON SEQUENCE "public"."channels_id_seq" TO "anon";
GRANT ALL ON SEQUENCE "public"."channels_id_seq" TO "authenticated";
GRANT ALL ON SEQUENCE "public"."channels_id_seq" TO "service_role";



GRANT ALL ON TABLE "public"."customer_channel_rules" TO "anon";
GRANT ALL ON TABLE "public"."customer_channel_rules" TO "authenticated";
GRANT ALL ON TABLE "public"."customer_channel_rules" TO "service_role";



GRANT ALL ON SEQUENCE "public"."customer_channel_rules_id_seq" TO "anon";
GRANT ALL ON SEQUENCE "public"."customer_channel_rules_id_seq" TO "authenticated";
GRANT ALL ON SEQUENCE "public"."customer_channel_rules_id_seq" TO "service_role";



GRANT ALL ON TABLE "public"."customers" TO "anon";
GRANT ALL ON TABLE "public"."customers" TO "authenticated";
GRANT ALL ON TABLE "public"."customers" TO "service_role";



GRANT ALL ON SEQUENCE "public"."customers_id_seq" TO "anon";
GRANT ALL ON SEQUENCE "public"."customers_id_seq" TO "authenticated";
GRANT ALL ON SEQUENCE "public"."customers_id_seq" TO "service_role";



GRANT ALL ON TABLE "public"."dim_date" TO "anon";
GRANT ALL ON TABLE "public"."dim_date" TO "authenticated";
GRANT ALL ON TABLE "public"."dim_date" TO "service_role";



GRANT ALL ON TABLE "public"."product_variants" TO "anon";
GRANT ALL ON TABLE "public"."product_variants" TO "authenticated";
GRANT ALL ON TABLE "public"."product_variants" TO "service_role";



GRANT ALL ON TABLE "public"."products" TO "anon";
GRANT ALL ON TABLE "public"."products" TO "authenticated";
GRANT ALL ON TABLE "public"."products" TO "service_role";



GRANT ALL ON TABLE "public"."inventory_consolidated" TO "anon";
GRANT ALL ON TABLE "public"."inventory_consolidated" TO "authenticated";
GRANT ALL ON TABLE "public"."inventory_consolidated" TO "service_role";



GRANT ALL ON TABLE "public"."warehouse_stock" TO "anon";
GRANT ALL ON TABLE "public"."warehouse_stock" TO "authenticated";
GRANT ALL ON TABLE "public"."warehouse_stock" TO "service_role";



GRANT ALL ON TABLE "public"."warehouses" TO "anon";
GRANT ALL ON TABLE "public"."warehouses" TO "authenticated";
GRANT ALL ON TABLE "public"."warehouses" TO "service_role";



GRANT ALL ON TABLE "public"."inventory_general" TO "anon";
GRANT ALL ON TABLE "public"."inventory_general" TO "authenticated";
GRANT ALL ON TABLE "public"."inventory_general" TO "service_role";



GRANT ALL ON TABLE "public"."inventory_movements" TO "anon";
GRANT ALL ON TABLE "public"."inventory_movements" TO "authenticated";
GRANT ALL ON TABLE "public"."inventory_movements" TO "service_role";



GRANT ALL ON SEQUENCE "public"."inventory_movements_id_seq" TO "anon";
GRANT ALL ON SEQUENCE "public"."inventory_movements_id_seq" TO "authenticated";
GRANT ALL ON SEQUENCE "public"."inventory_movements_id_seq" TO "service_role";



GRANT ALL ON TABLE "public"."inventory_planning_facts" TO "anon";
GRANT ALL ON TABLE "public"."inventory_planning_facts" TO "authenticated";
GRANT ALL ON TABLE "public"."inventory_planning_facts" TO "service_role";



GRANT ALL ON TABLE "public"."manual_corrections" TO "anon";
GRANT ALL ON TABLE "public"."manual_corrections" TO "authenticated";
GRANT ALL ON TABLE "public"."manual_corrections" TO "service_role";



GRANT ALL ON SEQUENCE "public"."manual_corrections_id_seq" TO "anon";
GRANT ALL ON SEQUENCE "public"."manual_corrections_id_seq" TO "authenticated";
GRANT ALL ON SEQUENCE "public"."manual_corrections_id_seq" TO "service_role";



GRANT ALL ON TABLE "public"."ml_tokens" TO "anon";
GRANT ALL ON TABLE "public"."ml_tokens" TO "authenticated";
GRANT ALL ON TABLE "public"."ml_tokens" TO "service_role";



GRANT ALL ON SEQUENCE "public"."ml_tokens_id_seq" TO "anon";
GRANT ALL ON SEQUENCE "public"."ml_tokens_id_seq" TO "authenticated";
GRANT ALL ON SEQUENCE "public"."ml_tokens_id_seq" TO "service_role";



GRANT ALL ON TABLE "public"."order_items" TO "anon";
GRANT ALL ON TABLE "public"."order_items" TO "authenticated";
GRANT ALL ON TABLE "public"."order_items" TO "service_role";



GRANT ALL ON SEQUENCE "public"."order_items_id_seq" TO "anon";
GRANT ALL ON SEQUENCE "public"."order_items_id_seq" TO "authenticated";
GRANT ALL ON SEQUENCE "public"."order_items_id_seq" TO "service_role";



GRANT ALL ON TABLE "public"."orders" TO "anon";
GRANT ALL ON TABLE "public"."orders" TO "authenticated";
GRANT ALL ON TABLE "public"."orders" TO "service_role";



GRANT ALL ON TABLE "public"."orders_audit" TO "anon";
GRANT ALL ON TABLE "public"."orders_audit" TO "authenticated";
GRANT ALL ON TABLE "public"."orders_audit" TO "service_role";



GRANT ALL ON SEQUENCE "public"."orders_audit_id_seq" TO "anon";
GRANT ALL ON SEQUENCE "public"."orders_audit_id_seq" TO "authenticated";
GRANT ALL ON SEQUENCE "public"."orders_audit_id_seq" TO "service_role";



GRANT ALL ON SEQUENCE "public"."orders_id_seq" TO "anon";
GRANT ALL ON SEQUENCE "public"."orders_id_seq" TO "authenticated";
GRANT ALL ON SEQUENCE "public"."orders_id_seq" TO "service_role";



GRANT ALL ON TABLE "public"."product_catalog" TO "anon";
GRANT ALL ON TABLE "public"."product_catalog" TO "authenticated";
GRANT ALL ON TABLE "public"."product_catalog" TO "service_role";



GRANT ALL ON SEQUENCE "public"."product_catalog_id_seq" TO "anon";
GRANT ALL ON SEQUENCE "public"."product_catalog_id_seq" TO "authenticated";
GRANT ALL ON SEQUENCE "public"."product_catalog_id_seq" TO "service_role";



GRANT ALL ON TABLE "public"."product_families" TO "anon";
GRANT ALL ON TABLE "public"."product_families" TO "authenticated";
GRANT ALL ON TABLE "public"."product_families" TO "service_role";



GRANT ALL ON TABLE "public"."product_inventory_settings" TO "anon";
GRANT ALL ON TABLE "public"."product_inventory_settings" TO "authenticated";
GRANT ALL ON TABLE "public"."product_inventory_settings" TO "service_role";



GRANT ALL ON SEQUENCE "public"."product_inventory_settings_id_seq" TO "anon";
GRANT ALL ON SEQUENCE "public"."product_inventory_settings_id_seq" TO "authenticated";
GRANT ALL ON SEQUENCE "public"."product_inventory_settings_id_seq" TO "service_role";



GRANT ALL ON SEQUENCE "public"."product_variants_id_seq" TO "anon";
GRANT ALL ON SEQUENCE "public"."product_variants_id_seq" TO "authenticated";
GRANT ALL ON SEQUENCE "public"."product_variants_id_seq" TO "service_role";



GRANT ALL ON SEQUENCE "public"."products_id_seq" TO "anon";
GRANT ALL ON SEQUENCE "public"."products_id_seq" TO "authenticated";
GRANT ALL ON SEQUENCE "public"."products_id_seq" TO "service_role";



GRANT ALL ON TABLE "public"."relbase_product_mappings" TO "anon";
GRANT ALL ON TABLE "public"."relbase_product_mappings" TO "authenticated";
GRANT ALL ON TABLE "public"."relbase_product_mappings" TO "service_role";



GRANT ALL ON SEQUENCE "public"."relbase_product_mappings_id_seq" TO "anon";
GRANT ALL ON SEQUENCE "public"."relbase_product_mappings_id_seq" TO "authenticated";
GRANT ALL ON SEQUENCE "public"."relbase_product_mappings_id_seq" TO "service_role";



GRANT ALL ON TABLE "public"."sku_mappings" TO "anon";
GRANT ALL ON TABLE "public"."sku_mappings" TO "authenticated";
GRANT ALL ON TABLE "public"."sku_mappings" TO "service_role";



GRANT ALL ON TABLE "public"."sales_facts_mv" TO "anon";
GRANT ALL ON TABLE "public"."sales_facts_mv" TO "authenticated";
GRANT ALL ON TABLE "public"."sales_facts_mv" TO "service_role";



GRANT ALL ON SEQUENCE "public"."sku_mappings_id_seq" TO "anon";
GRANT ALL ON SEQUENCE "public"."sku_mappings_id_seq" TO "authenticated";
GRANT ALL ON SEQUENCE "public"."sku_mappings_id_seq" TO "service_role";



GRANT ALL ON TABLE "public"."sync_logs" TO "anon";
GRANT ALL ON TABLE "public"."sync_logs" TO "authenticated";
GRANT ALL ON TABLE "public"."sync_logs" TO "service_role";



GRANT ALL ON SEQUENCE "public"."sync_logs_id_seq" TO "anon";
GRANT ALL ON SEQUENCE "public"."sync_logs_id_seq" TO "authenticated";
GRANT ALL ON SEQUENCE "public"."sync_logs_id_seq" TO "service_role";



GRANT ALL ON TABLE "public"."users" TO "anon";
GRANT ALL ON TABLE "public"."users" TO "authenticated";
GRANT ALL ON TABLE "public"."users" TO "service_role";



GRANT ALL ON SEQUENCE "public"."users_id_seq" TO "anon";
GRANT ALL ON SEQUENCE "public"."users_id_seq" TO "authenticated";
GRANT ALL ON SEQUENCE "public"."users_id_seq" TO "service_role";



GRANT ALL ON TABLE "public"."v_low_stock_products" TO "anon";
GRANT ALL ON TABLE "public"."v_low_stock_products" TO "authenticated";
GRANT ALL ON TABLE "public"."v_low_stock_products" TO "service_role";



GRANT ALL ON TABLE "public"."v_orders_full" TO "anon";
GRANT ALL ON TABLE "public"."v_orders_full" TO "authenticated";
GRANT ALL ON TABLE "public"."v_orders_full" TO "service_role";



GRANT ALL ON TABLE "public"."v_product_conversion" TO "anon";
GRANT ALL ON TABLE "public"."v_product_conversion" TO "authenticated";
GRANT ALL ON TABLE "public"."v_product_conversion" TO "service_role";



GRANT ALL ON TABLE "public"."v_sales_by_channel" TO "anon";
GRANT ALL ON TABLE "public"."v_sales_by_channel" TO "authenticated";
GRANT ALL ON TABLE "public"."v_sales_by_channel" TO "service_role";



GRANT ALL ON TABLE "public"."warehouse_stock_by_lot" TO "anon";
GRANT ALL ON TABLE "public"."warehouse_stock_by_lot" TO "authenticated";
GRANT ALL ON TABLE "public"."warehouse_stock_by_lot" TO "service_role";



GRANT ALL ON SEQUENCE "public"."warehouse_stock_id_seq" TO "anon";
GRANT ALL ON SEQUENCE "public"."warehouse_stock_id_seq" TO "authenticated";
GRANT ALL ON SEQUENCE "public"."warehouse_stock_id_seq" TO "service_role";



GRANT ALL ON SEQUENCE "public"."warehouses_id_seq" TO "anon";
GRANT ALL ON SEQUENCE "public"."warehouses_id_seq" TO "authenticated";
GRANT ALL ON SEQUENCE "public"."warehouses_id_seq" TO "service_role";









ALTER DEFAULT PRIVILEGES FOR ROLE "postgres" IN SCHEMA "public" GRANT ALL ON SEQUENCES TO "postgres";
ALTER DEFAULT PRIVILEGES FOR ROLE "postgres" IN SCHEMA "public" GRANT ALL ON SEQUENCES TO "anon";
ALTER DEFAULT PRIVILEGES FOR ROLE "postgres" IN SCHEMA "public" GRANT ALL ON SEQUENCES TO "authenticated";
ALTER DEFAULT PRIVILEGES FOR ROLE "postgres" IN SCHEMA "public" GRANT ALL ON SEQUENCES TO "service_role";






ALTER DEFAULT PRIVILEGES FOR ROLE "postgres" IN SCHEMA "public" GRANT ALL ON FUNCTIONS TO "postgres";
ALTER DEFAULT PRIVILEGES FOR ROLE "postgres" IN SCHEMA "public" GRANT ALL ON FUNCTIONS TO "anon";
ALTER DEFAULT PRIVILEGES FOR ROLE "postgres" IN SCHEMA "public" GRANT ALL ON FUNCTIONS TO "authenticated";
ALTER DEFAULT PRIVILEGES FOR ROLE "postgres" IN SCHEMA "public" GRANT ALL ON FUNCTIONS TO "service_role";






ALTER DEFAULT PRIVILEGES FOR ROLE "postgres" IN SCHEMA "public" GRANT ALL ON TABLES TO "postgres";
ALTER DEFAULT PRIVILEGES FOR ROLE "postgres" IN SCHEMA "public" GRANT ALL ON TABLES TO "anon";
ALTER DEFAULT PRIVILEGES FOR ROLE "postgres" IN SCHEMA "public" GRANT ALL ON TABLES TO "authenticated";
ALTER DEFAULT PRIVILEGES FOR ROLE "postgres" IN SCHEMA "public" GRANT ALL ON TABLES TO "service_role";































drop extension if exists "pg_net";

alter table "public"."sku_mappings" drop constraint "chk_pattern_type";

alter table "public"."warehouses" drop constraint "warehouses_update_method_check";

drop materialized view if exists "public"."sales_facts_mv";

alter table "public"."sku_mappings" add constraint "chk_pattern_type" CHECK (((pattern_type)::text = ANY ((ARRAY['exact'::character varying, 'prefix'::character varying, 'suffix'::character varying, 'regex'::character varying, 'contains'::character varying])::text[]))) not valid;

alter table "public"."sku_mappings" validate constraint "chk_pattern_type";

alter table "public"."warehouses" add constraint "warehouses_update_method_check" CHECK (((update_method)::text = ANY ((ARRAY['manual_upload'::character varying, 'api'::character varying])::text[]))) not valid;

alter table "public"."warehouses" validate constraint "warehouses_update_method_check";

create materialized view "public"."sales_facts_mv" as  SELECT (to_char(o.order_date, 'YYYYMMDD'::text))::integer AS date_id,
    o.order_date,
    o.channel_id,
    o.customer_id,
    o.source,
    oi.product_sku AS original_sku,
    COALESCE(pc_direct.sku, pc_master.sku, pc_mapped.sku, pc_mapped_master.sku) AS catalog_sku,
    COALESCE(pc_direct.sku_primario, pc_master.sku_primario, pc_mapped.sku_primario, pc_mapped_master.sku_primario) AS sku_primario,
    COALESCE(pc_direct.product_name, pc_master.master_box_name, pc_mapped.product_name, pc_mapped_master.master_box_name, (oi.product_name)::text) AS product_name,
    COALESCE(pc_direct.category, pc_master.category, pc_mapped.category, pc_mapped_master.category) AS category,
    COALESCE(pc_direct.package_type, pc_master.package_type, pc_mapped.package_type, pc_mapped_master.package_type) AS package_type,
    COALESCE(pc_direct.brand, pc_master.brand, pc_mapped.brand, pc_mapped_master.brand) AS brand,
    COALESCE(pc_direct.language, pc_master.language, pc_mapped.language, pc_mapped_master.language) AS language,
    COALESCE(pc_direct.units_per_display, pc_mapped.units_per_display, pc_mapped_master.units_per_display, 1) AS units_per_display,
    COALESCE(pc_master.items_per_master_box, pc_mapped_master.items_per_master_box, pc_direct.items_per_master_box, pc_mapped.items_per_master_box) AS items_per_master_box,
        CASE
            WHEN (pc_master.sku IS NOT NULL) THEN true
            WHEN (pc_mapped_master.sku IS NOT NULL) THEN true
            ELSE false
        END AS is_caja_master,
        CASE
            WHEN (pc_direct.sku IS NOT NULL) THEN 'direct'::text
            WHEN (pc_master.sku IS NOT NULL) THEN 'caja_master'::text
            WHEN (pc_mapped.sku IS NOT NULL) THEN 'sku_mapping'::text
            WHEN (pc_mapped_master.sku IS NOT NULL) THEN 'sku_mapping_caja_master'::text
            ELSE 'unmapped'::text
        END AS match_type,
    sm.rule_name AS mapping_rule,
    COALESCE(sm.quantity_multiplier, 1) AS quantity_multiplier,
    ch.name AS channel_name,
    c.name AS customer_name,
    c.rut AS customer_rut,
    oi.quantity AS original_units_sold,
    (oi.quantity * COALESCE(sm.quantity_multiplier, 1)) AS units_sold,
    oi.subtotal AS revenue,
    oi.unit_price,
    oi.total,
    oi.tax_amount,
    o.id AS order_id,
    o.external_id AS order_external_id,
    o.invoice_status,
    o.payment_status,
    o.status AS order_status,
    o.created_at AS order_created_at
   FROM ((((((((public.orders o
     JOIN public.order_items oi ON ((o.id = oi.order_id)))
     LEFT JOIN public.product_catalog pc_direct ON ((((pc_direct.sku)::text = upper((oi.product_sku)::text)) AND (pc_direct.is_active = true))))
     LEFT JOIN public.product_catalog pc_master ON ((((pc_master.sku_master)::text = upper((oi.product_sku)::text)) AND (pc_master.is_active = true) AND (pc_direct.sku IS NULL))))
     LEFT JOIN public.sku_mappings sm ON ((((sm.source_pattern)::text = upper((oi.product_sku)::text)) AND ((sm.pattern_type)::text = 'exact'::text) AND (sm.is_active = true) AND (pc_direct.sku IS NULL) AND (pc_master.sku IS NULL))))
     LEFT JOIN public.product_catalog pc_mapped ON ((((pc_mapped.sku)::text = (sm.target_sku)::text) AND (pc_mapped.is_active = true))))
     LEFT JOIN public.product_catalog pc_mapped_master ON ((((pc_mapped_master.sku_master)::text = (sm.target_sku)::text) AND (pc_mapped_master.is_active = true) AND (pc_mapped.sku IS NULL))))
     LEFT JOIN public.channels ch ON ((o.channel_id = ch.id)))
     LEFT JOIN public.customers c ON ((o.customer_id = c.id)))
  WHERE (((o.invoice_status)::text = ANY ((ARRAY['accepted'::character varying, 'accepted_objection'::character varying])::text[])) AND ((o.status)::text <> 'cancelled'::text));



