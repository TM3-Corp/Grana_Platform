-- Fix audit trigger to not reference dropped columns
--
-- The corrected_by and is_corrected columns were dropped in migration 20260113000001_database_cleanup.sql
-- but the audit_order_changes trigger still referenced them, causing all order
-- INSERT/UPDATE operations to fail with:
--   - record "new" has no field "corrected_by"
--   - record "new" has no field "is_corrected"
--
-- Solution: Remove both references and use 'system' and 'system_update' constants

CREATE OR REPLACE FUNCTION "public"."audit_order_changes"() RETURNS "trigger"
    LANGUAGE "plpgsql"
    AS $$
BEGIN
    -- Solo auditar si hay cambios reales
    IF (OLD.channel_id IS DISTINCT FROM NEW.channel_id) THEN
        INSERT INTO orders_audit (order_id, field_changed, old_value, new_value, changed_by, change_type)
        VALUES (NEW.id, 'channel_id', OLD.channel_id::text, NEW.channel_id::text,
                'system', 'system_update');
    END IF;

    IF (OLD.total IS DISTINCT FROM NEW.total) THEN
        INSERT INTO orders_audit (order_id, field_changed, old_value, new_value, changed_by, change_type)
        VALUES (NEW.id, 'total', OLD.total::text, NEW.total::text,
                'system', 'system_update');
    END IF;

    IF (OLD.customer_id IS DISTINCT FROM NEW.customer_id) THEN
        INSERT INTO orders_audit (order_id, field_changed, old_value, new_value, changed_by, change_type)
        VALUES (NEW.id, 'customer_id', OLD.customer_id::text, NEW.customer_id::text,
                'system', 'system_update');
    END IF;

    RETURN NEW;
END;
$$;

ALTER FUNCTION "public"."audit_order_changes"() OWNER TO "postgres";
