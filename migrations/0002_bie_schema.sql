CREATE TABLE IF NOT EXISTS business_profiles (
  id TEXT PRIMARY KEY,
  user_id TEXT NOT NULL UNIQUE,
  -- Identity
  business_name TEXT,
  vertical TEXT,
  city TEXT,
  address TEXT,
  website_url TEXT,
  phone TEXT,
  hours_json TEXT,
  -- Products/Services
  services_json TEXT,
  avg_ticket_usd INTEGER,
  -- Customers
  customer_profile TEXT,
  customer_avg_age TEXT,
  -- Brand
  brand_voice_words TEXT,
  brand_sample_good TEXT,
  brand_sample_bad TEXT,
  -- Competition
  competitors_json TEXT,
  -- Goals
  review_target INTEGER,
  monthly_revenue_goal INTEGER,
  biggest_pain TEXT,
  -- Seasonality
  slow_months TEXT,
  busy_months TEXT,
  -- Marketing history
  past_channels TEXT,
  what_worked TEXT,
  -- Meta
  bie_score INTEGER DEFAULT 0,
  updated_at TEXT DEFAULT (datetime('now')),
  created_at TEXT DEFAULT (datetime('now'))
);