-- Create payments table
CREATE TABLE IF NOT EXISTS public.payments (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL REFERENCES public.users(id),
    stripe_session_id TEXT NOT NULL UNIQUE,
    amount_total INTEGER NOT NULL,
    currency TEXT NOT NULL,
    status TEXT NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    price_id TEXT,
    vip_level INTEGER,
    vip_duration TEXT
);

-- Add vip columns to users table
ALTER TABLE public.users 
ADD COLUMN IF NOT EXISTS vip_level INTEGER DEFAULT 0,
ADD COLUMN IF NOT EXISTS vip_expire_at TIMESTAMPTZ;

-- Comments
COMMENT ON COLUMN public.users.vip_level IS '0: Normal, 1: Pro, 2: Premium';
COMMENT ON COLUMN public.users.vip_expire_at IS 'VIP expiration timestamp';
