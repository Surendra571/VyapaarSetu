import React, { createContext, useContext, useState, useEffect } from 'react';

export type Language = 'en' | 'hi';

interface Translations {
  [key: string]: {
    en: string;
    hi: string;
  };
}

export const translations: Translations = {
  // Navigation
  'nav.home': { en: 'Home', hi: 'होम' },
  'nav.catalogue': { en: 'Catalogue', hi: 'कैटलॉग' },
  'nav.ai_order': { en: 'AI Order', hi: 'AI आर्डर' },
  'nav.my_orders': { en: 'My Orders', hi: 'मेरे आर्डर्स' },
  'nav.account': { en: 'Account', hi: 'खाता' },
  'nav.desk': { en: 'Order Desk', hi: 'आर्डर डेस्क' },
  'nav.tally_export': { en: 'Tally Export', hi: 'टैली एक्सपोर्ट' },
  
  // Header & Banner
  'banner.title': { en: 'Smart Order. Better Business.', hi: 'स्मार्ट आर्डर। बेहतर व्यापार।' },
  'banner.subtitle': { en: 'Get the best prices, schemes and stock — all in one place.', hi: 'सबसे अच्छे दाम, स्कीमें और स्टॉक — सब एक ही जगह।' },
  'banner.cta': { en: 'Start New Order', hi: 'नया आर्डर शुरू करें' },
  'search.placeholder': { en: 'Search products... (e.g. biscuit, detergent)', hi: 'सामान खोजें... (जैसे बिस्कुट, डिटर्जेंट)' },
  
  // Metric Cards
  'stats.credit_limit': { en: 'Credit Limit', hi: 'क्रेडिट सीमा' },
  'stats.available': { en: 'Available', hi: 'उपलब्ध' },
  'stats.outstanding': { en: 'Outstanding', hi: 'बाकी रकम' },
  'stats.view_details': { en: 'View Details', hi: 'विवरण देखें' },
  'stats.active_schemes': { en: 'Active Schemes', hi: 'सक्रिय स्कीमें' },
  'stats.view_offers': { en: 'View Offers', hi: 'ऑफ़र देखें' },
  'stats.recent_orders': { en: 'Recent Orders', hi: 'हाल के आर्डर्स' },
  'stats.view_all': { en: 'View All', hi: 'सभी देखें' },

  // Catalogue
  'cat.filter_products': { en: 'Filter Products', hi: 'फ़िल्टर करें' },
  'cat.clear_all': { en: 'Clear All', hi: 'साफ़ करें' },
  'cat.categories': { en: 'Categories', hi: 'श्रेणियाँ' },
  'cat.availability': { en: 'Availability', hi: 'उपलब्धता' },
  'cat.schemes': { en: 'Schemes', hi: 'स्कीमें' },
  'cat.in_stock': { en: 'In Stock', hi: 'स्टॉक में है' },
  'cat.low_stock': { en: 'Low Stock', hi: 'कम स्टॉक' },
  'cat.out_of_stock': { en: 'Out of Stock', hi: 'स्टॉक खत्म' },
  'cat.cases_available': { en: 'cases available', hi: 'पेटी उपलब्ध' },
  'cat.add_to_cart': { en: 'Add to Cart', hi: 'कार्ट में जोड़ें' },
  'cat.currently_unavailable': { en: 'Currently Unavailable', hi: 'फ़िलहाल अनुपलब्ध' },
  'cat.special_scheme': { en: 'Special Scheme', hi: 'विशेष स्कीम' },

  // Cart & Order
  'cart.title': { en: 'Your Cart', hi: 'आपकी कार्ट' },
  'cart.subtotal': { en: 'Subtotal', hi: 'उप-योग' },
  'cart.scheme_discount': { en: 'Scheme Discount', hi: 'स्कीम छूट' },
  'cart.free_goods': { en: 'Free Goods', hi: 'मुफ़्त माल' },
  'cart.final_total': { en: 'Total Amount', hi: 'कुल रकम' },
  'cart.place_order': { en: 'Confirm & Place Order', hi: 'आर्डर पक्का करें' },
  'cart.empty': { en: 'Your cart is empty', hi: 'आपकी कार्ट खाली है' },

  // AI Order
  'ai.title': { en: 'AI WhatsApp Order Capture', hi: 'AI व्हाट्सएप आर्डर कैप्चर' },
  'ai.subtitle': { en: 'Type, paste or speak your order in Hindi or Hinglish.', hi: 'हिंदी या हिंगलिश में अपना आर्डर लिखें, पेस्ट करें या बोलें।' },
  'ai.extract_button': { en: 'Extract Items with AI', hi: 'AI से सामान पहचानें' },
  'ai.original_phrase': { en: 'Original Text', hi: 'मूल शब्द' },
  'ai.matched_sku': { en: 'Matched SKU', hi: 'पहचाना गया सामान' },
  'ai.confidence': { en: 'Confidence', hi: 'सटीकता' },
};

interface LanguageContextType {
  language: Language;
  setLanguage: (lang: Language) => void;
  t: (key: string) => string;
}

const LanguageContext = createContext<LanguageContextType | undefined>(undefined);

export const LanguageProvider: React.FC<{ children: React.ReactNode }> = ({ children }) => {
  const [language, setLanguageState] = useState<Language>(() => {
    return (localStorage.getItem('vyapaar_lang') as Language) || 'en';
  });

  const setLanguage = (lang: Language) => {
    setLanguageState(lang);
    localStorage.setItem('vyapaar_lang', lang);
  };

  const t = (key: string): string => {
    if (translations[key] && translations[key][language]) {
      return translations[key][language];
    }
    return key;
  };

  return (
    <LanguageContext.Provider value={{ language, setLanguage, t }}>
      {children}
    </LanguageContext.Provider>
  );
};

export const useLanguage = () => {
  const context = useContext(LanguageContext);
  if (!context) {
    throw new Error('useLanguage must be used within a LanguageProvider');
  }
  return context;
};
