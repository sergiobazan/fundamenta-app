BEGIN;
CREATE OR REPLACE VIEW user_activity_feed AS
 SELECT 'event:'||id AS event_id, user_id, user_id AS actor_id, 'human'::text AS actor_type,
 action,outcome,resource_type,resource_id,company_rpj,fiscal_year,scope,created_at,
 'recorded'::text AS source FROM user_activity_events
 UNION ALL
 SELECT 'registration:'||id,id,id,'human','account.register','success','user',id::text,
 NULL,NULL,NULL,created_at,'historical'
 FROM app_users u WHERE NOT EXISTS (SELECT 1 FROM user_activity_events e
 WHERE e.user_id=u.id AND e.action='account.register')
 UNION ALL
 SELECT 'analysis:'||j.id,j.requested_by,j.requested_by,'human','analysis.request',
 'created','analysis',j.id::text,c.smv_rpj,j.fiscal_year,j.scope,j.created_at,'historical'
 FROM analysis_jobs j JOIN companies c ON c.id=j.company_id WHERE j.requested_by IS NOT NULL
 AND NOT EXISTS (SELECT 1 FROM user_activity_events e WHERE e.user_id=j.requested_by
 AND e.action='analysis.request' AND e.resource_type='analysis' AND e.resource_id=j.id::text)
 UNION ALL
 SELECT 'report:'||r.id,r.requested_by,r.requested_by,'human','report.request','created',
 'report',r.id::text,c.smv_rpj,r.fiscal_year,r.scope,r.created_at,'historical'
 FROM notes_reports r JOIN companies c ON c.id=r.company_id
 WHERE NOT EXISTS (SELECT 1 FROM user_activity_events e WHERE e.user_id=r.requested_by
 AND e.action='report.request' AND e.resource_type='report' AND e.resource_id=r.id::text)
 UNION ALL
 SELECT 'job-state:'||e.id,j.requested_by,NULL,'system','analysis.state',
 e.snapshot->>'status','analysis',j.id::text,c.smv_rpj,j.fiscal_year,j.scope,e.created_at,
 CASE WHEN e.kind='baseline' THEN 'baseline' ELSE 'recorded' END
 FROM analysis_job_events e JOIN analysis_jobs j ON j.id=e.job_id
 JOIN companies c ON c.id=j.company_id WHERE j.requested_by IS NOT NULL AND e.kind<>'step'
 UNION ALL
 SELECT 'report-state:'||r.id,r.requested_by,NULL,'system','report.state',r.status,
 'report',r.id::text,c.smv_rpj,r.fiscal_year,r.scope,r.completed_at,'snapshot'
 FROM notes_reports r JOIN companies c ON c.id=r.company_id WHERE r.completed_at IS NOT NULL
 UNION ALL
 SELECT 'audit:'||a.id,COALESCE(a.target_user_id,a.actor_id),a.actor_id,'admin',a.action,
 'success','user',a.target_user_id::text,NULL,NULL,NULL,a.created_at,'audit'
 FROM admin_audit_events a WHERE COALESCE(a.target_user_id,a.actor_id) IS NOT NULL
 AND a.action NOT IN ('user.inspect','user.activity.inspect');
COMMIT;
