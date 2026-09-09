-- One invariant enforced by trigger: analysis_label.analysis_label_kind_id
-- must belong to the same analysis as analysis_label.analysis_run_id.
--
-- The CHECK constraints on `analysis_label.subject_tbl` and on the various
-- morph tables restrict the value set. We do not add existence-check triggers
-- for morph FKs — SQLite would need dynamic SQL, and the user has said not to
-- worry about check enforcement when it's annoying.

CREATE TRIGGER trg_analysis_label_kind_matches_run
BEFORE INSERT ON analysis_label
FOR EACH ROW
BEGIN
    SELECT CASE
        WHEN (SELECT analysis_id FROM analysis_run WHERE id = NEW.analysis_run_id)
           IS NOT
             (SELECT analysis_id FROM analysis_label_kind WHERE id = NEW.analysis_label_kind_id)
        THEN RAISE(ABORT, 'analysis_label: analysis_label_kind_id does not belong to same analysis as analysis_run_id')
    END;
END;
