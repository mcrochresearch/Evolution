import { NextResponse } from 'next/server';
import { D1Database } from '@cloudflare/workers-types';
import { getBusinessProfile } from '../../../../lib/db';

export async function POST(request: Request) {
  try {
    const { businessId, userId } = await request.json();
    
    // Validate input
    if (!businessId || !userId) {
      return NextResponse.json({ error: 'Missing businessId or userId' }, { status: 400 });
    }

    // Get database connection
    const db = (globalThis as any).DB;
    
    // Get business profile
    const profile = await getBusinessProfile(db).bind(businessId).first();
    
    // If profile not found
    if (!profile) {
      return NextResponse.json({ error: 'Business profile not found' }, { status: 404 });
    }

    // Format response
    return NextResponse.json({
      profile: {
        id: profile.id,
        business_name: profile.business_name,
        vertical: profile.vertical,
        city: profile.city,
        address: profile.address,
        website_url: profile.website_url,
        phone: profile.phone,
        hours_json: profile.hours_json,
        services_json: profile.services_json,
        avg_ticket_usd: profile.avg_ticket_usd,
        customer_profile: profile.customer_profile,
        customer_avg_age: profile.customer_avg_age,
        brand_voice_words: profile.brand_voice_words,
        brand_sample_good: profile.brand_sample_good,
        brand_sample_bad: profile.brand_sample_bad,
        competitors_json: profile.competitors_json,
        review_target: profile.review_target,
        monthly_revenue_goal: profile.monthly_revenue_goal,
        biggest_pain: profile.biggest_pain,
        slow_months: profile.slow_months,
        busy_months: profile.busy_months,
        past_channels: profile.past_channels,
        what_worked: profile.what_worked,
        bie_score: profile.bie_score,
        updated_at: profile.updated_at,
        created_at: profile.created_at
      }
    });
  } catch (error) {
    console.error('BIE API Error:', error);
    return NextResponse.json({ error: 'Internal server error' }, { status: 500 });
  }
}