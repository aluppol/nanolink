try {
  const env_vars = ['DB_NAME', 'DB_USER', 'DB_PASS']
  const errors = []
  for (const v of env_vars) {
    if (!process.env[v]) errors.push(`Missing env var ${v}`)
  }

  if (errors.length > 0) throw new Error(errors.join('\n'))
    
  
  db = db.getSiblingDB(process.env.DB_NAME);

  db.createUser({
    user: process.env.DB_USER,
    pwd: process.env.DB_PASS,
    roles: [{
      role: 'readWrite',
      db: process.env.DB_NAME
    }]
  });

  db.getCollection('Urls').createIndex({ 'short_url': 1 }, { unique: true })
  
} catch (e) {
  print(`Error during initialization: ${e}`);
}
