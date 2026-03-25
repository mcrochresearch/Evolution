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

export type AgentMemory = {
  id: string;
  user_id: string;
  agent: string;
  memory_key: string;
  memory_value: string;
  created_at: string;
};

export type AdCampaign = {
  id: string;
  user_id: string;
  business_id: string;
  name: string;
  budget: number;
  start_date: string;
  end_date: string;
  status: string;
  created_at: string;
};

export type CmoReport = {
  id: string;
  user_id: string;
  report_type: string;
  data: string;
  generated_at: string;
};