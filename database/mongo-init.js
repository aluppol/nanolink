try {
  const env_vars = [
    'DB_NAME',
    'DB_CRUD_USER',
    'DB_CRUD_PASS',
    'DB_URLS_COLLECTION_NAME',
    'DB_REDIRECT_USER',
    'DB_REDIRECT_PASS',
  ]
  const errors = []
  for (const v of env_vars) {
    if (!process.env[v]) errors.push(`Missing env var ${v}`)
  }

  if (errors.length > 0) throw new Error(errors.join('\n'))
    
  
  db = db.getSiblingDB(process.env.DB_NAME);

  db.createUser({ // CRUD service
    user: process.env.DB_CRUD_USER,
    pwd: process.env.DB_CRUD_PASS,
    roles: [{
      role: 'readWrite',
      db: process.env.DB_NAME
    }]
  });


  db.createUser({ // redirect service
    user: process.env.DB_REDIRECT_USER,
    pwd: process.env.DB_REDIRECT_PASS,
    roles: [{
      role: 'read',
      db: process.env.DB_NAME
    }]
  });

  db.getCollection(process.env.DB_URLS_COLLECTION_NAME).createIndex({ 'short_url': 1 }, { unique: true })
  
} catch (e) {
  print(`Error during initialization: ${e}`);
}
