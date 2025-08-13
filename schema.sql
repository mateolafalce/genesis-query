DROP TABLE IF EXISTS comments;
DROP TABLE IF EXISTS upvotes;

CREATE TABLE comments (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  content TEXT NOT NULL CHECK(length(content) <= 512),
  ip_address TEXT NOT NULL UNIQUE,
  votes INTEGER NOT NULL DEFAULT 0,
  country_code TEXT(2), 
  created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS upvotes (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    comment_id INTEGER NOT NULL,
    ip_address TEXT NOT NULL,
    UNIQUE(comment_id, ip_address),
    FOREIGN KEY(comment_id) REFERENCES comments(id)
);
