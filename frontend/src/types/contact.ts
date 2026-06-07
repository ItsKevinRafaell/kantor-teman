// Contact types
export interface Contact {
  id: number;
  business_name: string;
  owner_name: string | null;
  phone_number: string;
  purchased_product: string | null;
  notes: string | null;
  lead_id?: number | null;
}

export interface ProjectData {
  id: string;
  lead_id: number;
  name: string;
  type: string;
  status: string;
  nominal: number;
  start_date: string | null;
  end_date: string | null;
  service_type?: string | null;
  contract_months?: number | null;
}

export interface ServiceItem {
  id: string;
  name: string;
  default_price: number;
  default_features: string[];
}

export interface ProductItem {
  id: string;
  name: string;
  base_price: number;
  features: string[];
  category_name: string | null;
  is_active: boolean;
  is_retainer?: boolean;
}