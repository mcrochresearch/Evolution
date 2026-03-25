import { D1Database } from '@cloudflare/workers-types';

export type BusinessProfile = {
  id: string;
  user_id: string;
  business_name: string;
  vertical: string;
  city: string;
  address: string;
  website_url: string;
  phone: string;
  hours_json: string;
  services_json: string;
  avg_ticket_usd: number;
  customer_profile: string;
  customer_avg_age: string;
  brand_voice_words: string;
  brand_sample_good: string;
  brand_sample_bad: string;
  competitors_json: string;
  review_target: number;
  monthly_revenue_goal: number;
  biggest_pain: string;
  slow_months: string;
  busy_months: string;
  past_channels: string;
  what_worked: string;
  bie_score: number;
  updated_at: string;
  created_at: string;
};

export const createBusinessProfile = (db: D1Database) => {
  return db.prepare(
    'INSERT INTO business_profiles (
      id, user_id, business_name, vertical, city, address, website_url, phone, hours_json, services_json, avg_ticket_usd, customer_profile, customer_avg_age, brand_voice_words, brand_sample_good, brand_sample_bad, competitors_json, review_target, monthly_revenue_goal, biggest_pain, slow_months, busy_months, past_channels, what_worked, bie_score, updated_at, created_at
    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)'
  );
};

export const getBusinessProfile = (db: D1Database) => {
  return db.prepare(
    'SELECT * FROM business_profiles WHERE id = ?'
  );
};

export const updateBusinessProfile = (db: D1Database) => {
  return db.prepare(
    'UPDATE business_profiles SET 
      user_id = ?,
      business_name = ?,
      vertical = ?,
      city = ?,
      address = ?,
      website_url = ?,
      phone = ?,
      hours_json = ?,
      services_json = ?,
      avg_ticket_usd = ?,
      customer_profile = ?,
      customer_avg_age = ?,
      brand_voice_words = ?,
      brand_sample_good = ?,
      brand_sample_bad = ?,
      competitors_json = ?,
      review_target = ?,
      monthly_revenue_goal = ?,
      biggest_pain = ?,
      slow_months = ?,
      busy_months = ?,
      past_channels = ?,
      what_worked = ?,
      bie_score = ?,
      updated_at = ?
    WHERE id = ?'
  );
};

export const deleteBusinessProfile = (db: D1Database) => {
  return db.prepare('DELETE FROM business_profiles WHERE id = ?');
};

export const listBusinessProfiles = (db: D1Database) => {
  return db.prepare('SELECT * FROM business_profiles');
};