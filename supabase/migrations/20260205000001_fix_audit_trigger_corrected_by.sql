-- Fix audit trigger to not reference dropped corrected_by column
--
-- The corrected_by column was dropped in migration 20260113000001_database_cleanup.sql
-- but the audit_order_changes trigger still referenced it, causing all order
-- INSERT/UPDATE operations to fail with: record "new" has no field "corrected_by"
--
-- Solution: Replace COALESCE(NEW.corrected_by, 'system') with just 'system'

CREATE OR REPLACE FUNCTION "public"."audit_order_changes"() RETURNS "trigger"
    LANGUAGE "plpgsql"
    AS $$
BEGIN
    -- Solo auditar si hay cambios reales
    IF (OLD.channel_id IS DISTINCT FROM NEW.channel_id) THEN
        INSERT INTO orders_audit (order_id, field_changed, old_value, new_value, changed_by, change_type)
        VALUES (NEW.id, 'channel_id', OLD.channel_id::text, NEW.channel_id::text,
                'system',
                CASE WHEN NEW.is_corrected THEN 'manual_correction' ELSE 'system_update' END);
    END IF;

    IF (OLD.total IS DISTINCT FROM NEW.total) THEN
        INSERT INTO orders_audit (order_id, field_changed, old_value, new_value, changed_by, change_type)
        VALUES (NEW.id, 'total', OLD.total::text, NEW.total::text,
                'system',
                CASE WHEN NEW.is_corrected THEN 'manual_correction' ELSE 'system_update' END);
    END IF;

    IF (OLD.customer_id IS DISTINCT FROM NEW.customer_id) THEN
        INSERT INTO orders_audit (order_id, field_changed, old_value, new_value, changed_by, change_type)
        VALUES (NEW.id, 'customer_id', OLD.customer_id::text, NEW.customer_id::text,
                'system',
                CASE WHEN NEW.is_corrected THEN 'manual_correction' ELSE 'system_update' END);
    END IF;

    RETURN NEW;
END;
$$;

ALTER FUNCTION "public"."audit_order_changes"() OWNER TO "postgres";
