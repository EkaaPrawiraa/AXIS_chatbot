MATCH (u:User {id: '6aca3b8b-ddcf-4428-824e-997f921d28d3'})-[r]->(n)
WITH u, type(r) AS relType, collect({r: r, n: n})[..5] AS items
UNWIND items AS item
WITH u, item.r AS r, item.n AS n
OPTIONAL MATCH (n)-[r2]->(m)
WHERE any(label IN labels(m) WHERE label IN ['Topic', 'Emotion', 'Thought', 'Behavior', 'Person', 'Trigger'])
WITH u, r, n, collect({r2: r2, m: m})[..2] AS related
UNWIND CASE WHEN related = [] THEN [{r2: null, m: null}] ELSE related END AS item2
RETURN u, r, n, item2.r2 AS r2, item2.m AS m;
