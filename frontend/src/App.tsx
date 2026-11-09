import { FormEvent, useCallback, useEffect, useMemo, useRef, useState } from 'react';
import {
  AlertCircle,
  AlertTriangle,
  ArrowDownToLine,
  ArrowRight,
  BadgeCheck,
  Box,
  BriefcaseBusiness,
  Building2,
  Camera,
  Check,
  CheckCircle2,
  ChevronDown,
  CircleHelp,
  ClipboardList,
  CreditCard,
  Download,
  FileSpreadsheet,
  Headphones,
  Home,
  KeyRound,
  LoaderCircle,
  LogOut,
  MapPin,
  Mic,
  MicOff,
  Minus,
  Package,
  Plus,
  Printer,
  RefreshCw,
  RotateCcw,
  Search,
  ShoppingBag,
  Smartphone,
  Sparkles,
  Store,
  Truck,
  UserRound,
  Wifi,
  WifiOff,
  X,
} from 'lucide-react';
import { api, getToken, setToken } from './api';
import type {
  AuthUser,
  BenefitDetail,
  CaptureLine,
  CaptureSession,
  ExportBatch,
  InactiveRetailerItem,
  InactiveRetailersResponse,
  OrderPreview,
  OrderRecord,
  RepeatOrderPreviewResponse,
  RetailerPrice,
  VanLoadingItem,
  VanLoadingListResponse,
} from './api';
import type { Product, Scheme } from './types';

export type Screen = 'login' | 'catalogue' | 'cart' | 'ai' | 'orders' | 'desk' | 'van' | 'inactivity' | 'exports' | 'account';
export type LoginRole = 'retailer' | 'desk';
export type LoginState = 'loading' | 'ready';

export const DESK_SCREENS: Screen[] = ['desk', 'van', 'inactivity', 'exports', 'account'];
export const RETAILER_SCREENS: Screen[] = ['catalogue', 'cart', 'ai', 'orders', 'account'];

export const getScreenFromPath = (pathname: string): Screen => {
  const clean = pathname.replace(/^\/+/, '').split('?')[0].split('#')[0].toLowerCase();
  switch (clean) {
    case 'login':
      return 'login';
    case 'cart':
      return 'cart';
    case 'ai':
      return 'ai';
    case 'orders':
    case 'my-orders':
      return 'orders';
    case 'desk':
    case 'order-desk':
      return 'desk';
    case 'van':
    case 'van-loading':
    case 'van-loading-list':
      return 'van';
    case 'inactivity':
    case 'inactive-retailers':
      return 'inactivity';
    case 'exports':
    case 'tally':
    case 'tally-export':
      return 'exports';
    case 'account':
    case 'profile':
      return 'account';
    case 'catalogue':
    case 'catalog':
    case '':
    default:
      return 'catalogue';
  }
};

export const getPathFromScreen = (scr: Screen): string => {
  if (scr === 'catalogue') return '/catalogue';
  return `/${scr}`;
};

interface LoginForm {
  phone: string;
  otp: string;
}

interface OfflineOrder {
  clientOrderId: string;
  items: { productId: string; productName: string; quantity: number }[];
  deliveryNotes: string;
  createdAt: string;
  status: 'PENDING_SYNC' | 'SYNC_FAILED';
  error?: string;
}

interface CaptureResolution {
  productId: string;
  quantity: number;
  unit: '' | 'CASE' | 'PIECE';
  saveAlias: boolean;
}

const DEMO_ACCOUNTS: Record<LoginRole, LoginForm> = {
  retailer: { phone: '9826011111', otp: '123456' },
  desk: { phone: '9826000000', otp: '123456' },
};

const DEFAULT_AI_MESSAGE =
  'bhaiya 5 peti biscuit chhota, 2 peti washing powder 1 kilo, chai patti 250 wala 1 peti';

const NAV_ITEMS: { id: Screen; label: string; icon: typeof Home; roles: LoginRole[]; path: string }[] = [
  { id: 'catalogue', label: 'Catalogue', icon: Box, roles: ['retailer'], path: '/catalogue' },
  { id: 'ai', label: 'AI order capture', icon: Sparkles, roles: ['retailer'], path: '/ai' },
  { id: 'cart', label: 'Cart & checkout', icon: ShoppingBag, roles: ['retailer'], path: '/cart' },
  { id: 'orders', label: 'My orders', icon: ClipboardList, roles: ['retailer'], path: '/orders' },
  { id: 'desk', label: 'Order desk', icon: BriefcaseBusiness, roles: ['desk'], path: '/desk' },
  { id: 'van', label: 'Van loading list', icon: Truck, roles: ['desk'], path: '/van' },
  { id: 'inactivity', label: 'Retailer inactivity', icon: Store, roles: ['desk'], path: '/inactivity' },
  { id: 'exports', label: 'Tally export', icon: FileSpreadsheet, roles: ['desk'], path: '/exports' },
  { id: 'account', label: 'Account', icon: UserRound, roles: ['retailer', 'desk'], path: '/account' },
];

const formatMoney = (value: number | string | null | undefined) =>
  `₹${Number(value ?? 0).toLocaleString('en-IN', { minimumFractionDigits: 2, maximumFractionDigits: 2 })}`;

const friendlyCategory = (product: Product): string => {
  if (product.sku_code === 'SKU-BS-075') return 'Biscuits';
  if (product.sku_code === 'SKU-DT-1KG') return 'Detergents';
  if (product.sku_code === 'SKU-TE-250') return 'Tea & Beverage';
  return product.category;
};

const PRODUCT_IMAGE_BY_SKU: Record<string, string> = {
  'SKU-BS-075': '/images/products/SKU-BS-075.png',
  'SKU-DT-1KG': '/images/products/SKU-DT-1KG.png',
  'SKU-TE-250': '/images/products/SKU-TE-250.png',
};

const stockLabel = (cases: number) => {
  if (cases === 0) return { text: 'Out of stock', tone: 'rose' };
  if (cases < 100) return { text: 'Low stock', tone: 'amber' };
  return { text: 'In stock', tone: 'green' };
};

const errorMessage = (error: unknown) =>
  error instanceof Error ? error.message : 'Something went wrong. Please try again.';

function App() {
  const [user, setUser] = useState<AuthUser | null>(null);
  const [loginState, setLoginState] = useState<LoginState>('loading');
  const [loginRole, setLoginRole] = useState<LoginRole>('retailer');
  const [loginForm, setLoginForm] = useState<LoginForm>(DEMO_ACCOUNTS.retailer);
  const [loginBusy, setLoginBusy] = useState(false);
  const [authTab, setAuthTab] = useState<'signin' | 'signup'>('signin');
  const [signUpForm, setSignUpForm] = useState({
    phone: '',
    fullName: '',
    storeName: '',
    city: 'Jabalpur',
    address: '',
    gstNumber: '',
    otp: '123456',
  });
  const [otpNotice, setOtpNotice] = useState('');
  const [otpTimer, setOtpTimer] = useState(0);
  const [sendingOtp, setSendingOtp] = useState(false);
  const [accountNotFoundNotice, setAccountNotFoundNotice] = useState(false);
  const [screen, setScreen] = useState<Screen>(() => {
    if (typeof window !== 'undefined') {
      return getScreenFromPath(window.location.pathname);
    }
    return 'catalogue';
  });
  const [products, setProducts] = useState<Product[]>([]);
  const [schemes, setSchemes] = useState<Scheme[]>([]);
  const [orders, setOrders] = useState<OrderRecord[]>([]);
  const [deskOrders, setDeskOrders] = useState<OrderRecord[]>([]);
  const [exportBatches, setExportBatches] = useState<ExportBatch[]>([]);
  const [cart, setCart] = useState<Record<string, number>>({});
  const [cartPreview, setCartPreview] = useState<OrderPreview | null>(null);
  const [deliveryNotes, setDeliveryNotes] = useState('');
  const [query, setQuery] = useState('');
  const [category, setCategory] = useState('All');
  const [availability, setAvailability] = useState('All stock');
  const [rawMessage, setRawMessage] = useState(DEFAULT_AI_MESSAGE);
  const [capture, setCapture] = useState<CaptureSession | null>(null);
  const [captureResolution, setCaptureResolution] = useState<Record<string, CaptureResolution>>({});
  const [reviewedLines, setReviewedLines] = useState<string[]>([]);
  const [selectedDeskOrder, setSelectedDeskOrder] = useState<OrderRecord | null>(null);
  const [selectedOrder, setSelectedOrder] = useState<OrderRecord | null>(null);
  const [orderFilter, setOrderFilter] = useState('All');
  const [selectedExportOrders, setSelectedExportOrders] = useState<string[]>([]);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState('');
  const [notice, setNotice] = useState('');
  const [dataLoading, setDataLoading] = useState(false);

  // PWA / Offline salesman mode
  const [isOnline, setIsOnline] = useState(typeof navigator !== 'undefined' ? navigator.onLine : true);
  const [offlineQueue, setOfflineQueue] = useState<OfflineOrder[]>(() => {
    try {
      const saved = localStorage.getItem('vyapaar_offline_orders');
      return saved ? JSON.parse(saved) : [];
    } catch {
      return [];
    }
  });

  // Van Loading List
  const [vanData, setVanData] = useState<VanLoadingListResponse | null>(null);
  const [vanFromDate, setVanFromDate] = useState('');
  const [vanToDate, setVanToDate] = useState('');
  const [expandedVanSku, setExpandedVanSku] = useState<string | null>(null);

  // Retailer Inactivity
  const [inactivityData, setInactivityData] = useState<InactiveRetailersResponse | null>(null);
  const [inactivityDays, setInactivityDays] = useState(14);
  const [inactivitySearch, setInactivitySearch] = useState('');
  const [inactivityPage, setInactivityPage] = useState(1);

  // Multimodal AI
  const [aiMode, setAiMode] = useState<'text' | 'photo' | 'voice'>('text');
  const [photoFile, setPhotoFile] = useState<File | null>(null);
  const [voiceFile, setVoiceFile] = useState<File | null>(null);
  const [photoPreviewUrl, setPhotoPreviewUrl] = useState<string | null>(null);
  const [voiceAudioUrl, setVoiceAudioUrl] = useState<string | null>(null);
  const [isRecording, setIsRecording] = useState(false);
  const [uploadErrorModal, setUploadErrorModal] = useState<{
    mode: 'photo' | 'voice' | 'general';
    title: string;
    message: string;
  } | null>(null);
  const photoInputRef = useRef<HTMLInputElement | null>(null);
  const mediaRecorderRef = useRef<MediaRecorder | null>(null);
  const audioChunksRef = useRef<Blob[]>([]);

  const retryPhotoUpload = () => {
    setUploadErrorModal(null);
    setError('');
    setPhotoFile(null);
    setCapture(null);
    setTimeout(() => {
      photoInputRef.current?.click();
    }, 100);
  };

  const retryVoiceUpload = () => {
    setUploadErrorModal(null);
    setError('');
    setVoiceFile(null);
    setCapture(null);
  };

  useEffect(() => {
    if (photoFile) {
      const url = URL.createObjectURL(photoFile);
      setPhotoPreviewUrl(url);
      return () => URL.revokeObjectURL(url);
    }
    setPhotoPreviewUrl(null);
  }, [photoFile]);

  useEffect(() => {
    if (voiceFile) {
      const url = URL.createObjectURL(voiceFile);
      setVoiceAudioUrl(url);
      return () => URL.revokeObjectURL(url);
    }
    setVoiceAudioUrl(null);
  }, [voiceFile]);

  useEffect(() => {
    if (otpTimer <= 0) return;
    const interval = setInterval(() => {
      setOtpTimer((prev) => (prev > 0 ? prev - 1 : 0));
    }, 1000);
    return () => clearInterval(interval);
  }, [otpTimer]);

  // Repeat Order Preview Modal
  const [repeatPreview, setRepeatPreview] = useState<RepeatOrderPreviewResponse | null>(null);
  const [repeatSourceOrder, setRepeatSourceOrder] = useState<OrderRecord | null>(null);

  useEffect(() => {
    try {
      localStorage.setItem('vyapaar_offline_orders', JSON.stringify(offlineQueue));
    } catch {
      // Ignore quota errors
    }
  }, [offlineQueue]);

  useEffect(() => {
    const handleOnline = () => {
      setIsOnline(true);
      setNotice('Network connection restored.');
    };
    const handleOffline = () => {
      setIsOnline(false);
      setError('You are offline. Salesman offline mode active: orders will queue locally.');
    };
    window.addEventListener('online', handleOnline);
    window.addEventListener('offline', handleOffline);
    return () => {
      window.removeEventListener('online', handleOnline);
      window.removeEventListener('offline', handleOffline);
    };
  }, []);

  const loadRetailerData = useCallback(async () => {
    if (!getToken()) return;
    setDataLoading(true);
    setError('');
    try {
      const [profile, catalogue, priceList, activeSchemes, retailerOrders] = await Promise.all([
        api.me(),
        api.products(),
        api.retailerPrices(),
        api.schemes(),
        api.retailerOrders(),
      ]);
      setUser(profile);
      const pricesByProduct = new Map<string, RetailerPrice>(
        priceList.map((price) => [price.product_id, price]),
      );
      const completeProducts = catalogue.items.map((item) => {
        const price = pricesByProduct.get(item.id);
        const productSchemes = activeSchemes.filter((scheme) =>
          scheme.rules?.some((rule) => rule.qualifying_product_id === item.id),
        );
        return {
          ...item,
          category: friendlyCategory(item),
          default_dealer_price: Number(price?.effective_price ?? item.default_dealer_price),
          effective_price: Number(price?.effective_price ?? item.default_dealer_price),
          image_url: PRODUCT_IMAGE_BY_SKU[item.sku_code] ?? item.image_url,
          stock_cases: item.available_cases,
          active_schemes: productSchemes,
        };
      });
      setProducts(completeProducts);
      try {
        localStorage.setItem('vyapaar_cached_products', JSON.stringify(completeProducts));
      } catch {
        // Ignore quota error
      }
      setSchemes(activeSchemes);
      setOrders(retailerOrders.items);
    } catch (loadError) {
      setError(errorMessage(loadError));
      try {
        const cached = localStorage.getItem('vyapaar_cached_products');
        if (cached) {
          const parsed = JSON.parse(cached);
          if (Array.isArray(parsed) && parsed.length > 0) {
            setProducts(parsed);
          }
        }
      } catch {
        // Ignore JSON error
      }
    } finally {
      setDataLoading(false);
    }
  }, []);

  const loadDeskData = useCallback(async () => {
    if (!getToken()) return;
    setDataLoading(true);
    setError('');
    try {
      const [queue, batches] = await Promise.all([api.deskOrders(), api.exportBatches()]);
      setDeskOrders(queue.items);
      setExportBatches(batches.items);
    } catch (loadError) {
      setError(errorMessage(loadError));
    } finally {
      setDataLoading(false);
    }
  }, []);

  const loadVanData = useCallback(async () => {
    if (!getToken()) return;
    setDataLoading(true);
    setError('');
    try {
      const data = await api.vanLoadingList(vanFromDate || undefined, vanToDate || undefined);
      setVanData(data);
    } catch (err) {
      setError(errorMessage(err));
    } finally {
      setDataLoading(false);
    }
  }, [vanFromDate, vanToDate]);

  const loadInactivityData = useCallback(async (page = 1) => {
    if (!getToken()) return;
    setDataLoading(true);
    setError('');
    try {
      const data = await api.inactiveRetailers(inactivityDays, inactivitySearch || undefined, page);
      setInactivityData(data);
      setInactivityPage(data.page);
    } catch (err) {
      setError(errorMessage(err));
    } finally {
      setDataLoading(false);
    }
  }, [inactivityDays, inactivitySearch]);

  const loadUserData = useCallback(async (nextUser: AuthUser) => {
    if (nextUser.role === 'ROLE_RETAILER') {
      await loadRetailerData();
    } else {
      await loadDeskData();
    }
  }, [loadDeskData, loadRetailerData]);

  const showScreen = useCallback(
    (next: Screen, pushHistory = true) => {
      if (!getToken() && next !== 'login') {
        setScreen('login');
        if (pushHistory && typeof window !== 'undefined' && window.location.pathname !== '/login') {
          window.history.pushState({ screen: 'login' }, '', '/login');
        }
        return;
      }

      // Guard screens by authenticated role
      let effectiveNext = next;
      const currentRole: LoginRole = user?.role === 'ROLE_ORDER_DESK' ? 'desk' : 'retailer';
      if (user) {
        if (currentRole === 'desk' && !DESK_SCREENS.includes(next)) {
          effectiveNext = 'desk';
        } else if (currentRole === 'retailer' && !RETAILER_SCREENS.includes(next)) {
          effectiveNext = 'catalogue';
        }
      }

      setScreen(effectiveNext);
      setError('');
      setNotice('');
      const targetPath = getPathFromScreen(effectiveNext);
      if (pushHistory && typeof window !== 'undefined' && window.location.pathname !== targetPath) {
        window.history.pushState({ screen: effectiveNext }, '', targetPath);
      }
      if (effectiveNext === 'orders') void loadRetailerData();
      if (effectiveNext === 'desk' || effectiveNext === 'exports') void loadDeskData();
      if (effectiveNext === 'van') void loadVanData();
      if (effectiveNext === 'inactivity') void loadInactivityData(1);
    },
    [user, loadDeskData, loadInactivityData, loadRetailerData, loadVanData],
  );

  useEffect(() => {
    let active = true;
    const initialPath = typeof window !== 'undefined' ? window.location.pathname : '/';
    const initialScreen = getScreenFromPath(initialPath);

    if (!getToken()) {
      setLoginState('ready');
      if (initialScreen !== 'login') {
        if (initialPath !== '/' && initialPath !== '/catalogue') {
          const redirectParam = encodeURIComponent(initialPath + (window.location.search || ''));
          window.history.replaceState({ screen: 'login' }, '', `/login?redirect=${redirectParam}`);
        } else {
          window.history.replaceState({ screen: 'login' }, '', '/login');
        }
        setScreen('login');
      }
      return () => { active = false; };
    }

    api.me()
      .then(async (profile) => {
        if (!active) return;
        setUser(profile);
        const roleName = profile.role === 'ROLE_ORDER_DESK' ? 'desk' : 'retailer';
        setLoginRole(roleName);

        let targetScreen = initialScreen;
        if (targetScreen === 'login') {
          const searchParams = new URLSearchParams(window.location.search);
          const redirect = searchParams.get('redirect');
          if (redirect && redirect.startsWith('/') && redirect !== '/login') {
            const parsed = getScreenFromPath(redirect);
            targetScreen = roleName === 'desk'
              ? (DESK_SCREENS.includes(parsed) ? parsed : 'desk')
              : (RETAILER_SCREENS.includes(parsed) ? parsed : 'catalogue');
          } else {
            targetScreen = roleName === 'desk' ? 'desk' : 'catalogue';
          }
        } else if (roleName === 'retailer' && !RETAILER_SCREENS.includes(targetScreen)) {
          targetScreen = 'catalogue';
          setError('Desk screens are restricted to Order Desk operators.');
        } else if (roleName === 'desk' && !DESK_SCREENS.includes(targetScreen)) {
          targetScreen = 'desk';
        }

        setScreen(targetScreen);
        const path = getPathFromScreen(targetScreen);
        if (typeof window !== 'undefined' && window.location.pathname !== path) {
          window.history.replaceState({ screen: targetScreen }, '', path);
        }

        await loadUserData(profile);
        if (targetScreen === 'van') void loadVanData();
        if (targetScreen === 'inactivity') void loadInactivityData(1);
      })
      .catch(() => {
        if (active) {
          setToken(null);
          setUser(null);
          setScreen('login');
          window.history.replaceState({ screen: 'login' }, '', '/login');
          setError('Your session expired. Please sign in again.');
        }
      })
      .finally(() => {
        if (active) setLoginState('ready');
      });

    return () => { active = false; };
  }, [loadUserData, loadVanData, loadInactivityData]);

  useEffect(() => {
    const handlePopState = () => {
      const currentPath = window.location.pathname;
      const matched = getScreenFromPath(currentPath);
      setScreen(matched);
      setError('');
      setNotice('');
      if (matched === 'orders') void loadRetailerData();
      if (matched === 'desk' || matched === 'exports') void loadDeskData();
      if (matched === 'van') void loadVanData();
      if (matched === 'inactivity') void loadInactivityData(1);
    };
    window.addEventListener('popstate', handlePopState);
    return () => window.removeEventListener('popstate', handlePopState);
  }, [loadDeskData, loadInactivityData, loadRetailerData, loadVanData]);

  const visibleNav = useMemo(() => {
    const role: LoginRole = user?.role === 'ROLE_ORDER_DESK' ? 'desk' : 'retailer';
    return NAV_ITEMS.filter((item) => item.roles.includes(role));
  }, [user]);

  const filteredProducts = useMemo(() => {
    const normalized = query.trim().toLowerCase();
    return products.filter((product) => {
      const categoryMatches = category === 'All' || product.category === category;
      const queryMatches = !normalized || [
        product.name,
        product.sku_code,
        product.brand,
        product.category,
      ].some((field) => field.toLowerCase().includes(normalized));
      const stockMatches =
        availability === 'All stock' ||
        (availability === 'In stock' && product.available_cases >= 100) ||
        (availability === 'Low stock' && product.available_cases > 0 && product.available_cases < 100) ||
        (availability === 'Out of stock' && product.available_cases === 0);
      return categoryMatches && queryMatches && stockMatches;
    });
  }, [availability, category, products, query]);

  const cartItems = useMemo(
    () => Object.entries(cart)
      .map(([productId, quantity]) => ({
        product: products.find((item) => item.id === productId),
        quantity,
      }))
      .filter((item): item is { product: Product; quantity: number } =>
        Boolean(item.product) && item.quantity > 0,
      ),
    [cart, products],
  );
  const cartCount = cartItems.reduce((sum, item) => sum + item.quantity, 0);
  const cartEstimate = cartItems.reduce(
    (sum, item) => sum + Number(item.product.default_dealer_price) * item.quantity,
    0,
  );

  const quickSignIn = async (roleToLogin: LoginRole) => {
    const creds = DEMO_ACCOUNTS[roleToLogin];
    setLoginForm(creds);
    setLoginRole(roleToLogin);
    setLoginBusy(true);
    setError('');
    try {
      const response = await api.login(creds.phone, creds.otp);
      setToken(response.access_token);
      setUser(response.user);
      const roleName = response.user.role === 'ROLE_ORDER_DESK' ? 'desk' : 'retailer';
      setLoginRole(roleName);

      const targetScreen: Screen = roleName === 'desk' ? 'desk' : 'catalogue';
      showScreen(targetScreen);
      await loadUserData(response.user);
    } catch (err) {
      setError(errorMessage(err));
    } finally {
      setLoginBusy(false);
      setLoginState('ready');
    }
  };

  const handleSendOtp = async (targetPhone?: string) => {
    const raw = targetPhone ?? (authTab === 'signin' ? loginForm.phone : signUpForm.phone);
    const cleaned = raw.replace(/\D/g, '');
    const phone = cleaned.startsWith('91') && cleaned.length === 12 ? cleaned.slice(2) : cleaned;
    if (!phone || phone.length < 10) {
      setError('Please enter a valid 10-digit mobile number.');
      return;
    }
    setError('');
    setOtpNotice('');
    setSendingOtp(true);
    setAccountNotFoundNotice(false);
    try {
      const res = await api.sendOtp(phone);
      setOtpTimer(30);
      setOtpNotice(res.message || `OTP dispatched to +91 ******${phone.slice(-4)}. Enter OTP to verify.`);
    } catch (err) {
      setError(errorMessage(err));
    } finally {
      setSendingOtp(false);
    }
  };

  const signIn = async (event: FormEvent) => {
    event.preventDefault();
    setLoginBusy(true);
    setError('');
    setAccountNotFoundNotice(false);
    try {
      const response = await api.login(loginForm.phone, loginForm.otp);
      setToken(response.access_token);
      setUser(response.user);
      const roleName = response.user.role === 'ROLE_ORDER_DESK' ? 'desk' : 'retailer';
      setLoginRole(roleName);

      const params = new URLSearchParams(window.location.search);
      const redirect = params.get('redirect');
      let targetScreen: Screen = roleName === 'desk' ? 'desk' : 'catalogue';
      if (redirect && redirect.startsWith('/') && redirect !== '/login') {
        const parsed = getScreenFromPath(redirect);
        if (roleName === 'desk') {
          targetScreen = DESK_SCREENS.includes(parsed) ? parsed : 'desk';
        } else {
          targetScreen = RETAILER_SCREENS.includes(parsed) ? parsed : 'catalogue';
        }
      }

      showScreen(targetScreen);
      await loadUserData(response.user);
      if (targetScreen === 'van') void loadVanData();
      if (targetScreen === 'inactivity') void loadInactivityData(1);
    } catch (loginError) {
      const msg = errorMessage(loginError);
      setError(msg);
      if (msg.toLowerCase().includes('not found') || msg.toLowerCase().includes('no account found')) {
        setAccountNotFoundNotice(true);
      }
    } finally {
      setLoginBusy(false);
      setLoginState('ready');
    }
  };

  const signUp = async (event: FormEvent) => {
    event.preventDefault();
    setLoginBusy(true);
    setError('');
    setOtpNotice('');
    setAccountNotFoundNotice(false);
    const cleaned = signUpForm.phone.replace(/\D/g, '');
    const phone = cleaned.startsWith('91') && cleaned.length === 12 ? cleaned.slice(2) : cleaned;
    if (!phone || phone.length < 10) {
      setError('Please enter a valid 10-digit Indian mobile number.');
      setLoginBusy(false);
      return;
    }
    if (!signUpForm.fullName.trim()) {
      setError('Please enter the shop owner or contact name.');
      setLoginBusy(false);
      return;
    }
    if (!signUpForm.storeName.trim()) {
      setError('Please enter your Kirana / Shop name.');
      setLoginBusy(false);
      return;
    }
    if (!signUpForm.otp.trim()) {
      setError('Please enter the 6-digit OTP code.');
      setLoginBusy(false);
      return;
    }

    try {
      const response = await api.register({
        phone_number: phone,
        full_name: signUpForm.fullName.trim(),
        store_name: signUpForm.storeName.trim(),
        city: signUpForm.city.trim() || 'Jabalpur',
        address: signUpForm.address.trim() || 'Main Market, Jabalpur',
        gst_number: signUpForm.gstNumber.trim() || undefined,
        otp_code: signUpForm.otp.trim(),
      });
      setToken(response.access_token);
      setUser(response.user);
      setLoginRole('retailer');
      showScreen('catalogue');
      await loadUserData(response.user);
      setNotice(`Welcome ${response.user.full_name}! Your Kirana store account is ready with ₹50,000 credit line.`);
    } catch (err) {
      setError(errorMessage(err));
    } finally {
      setLoginBusy(false);
      setLoginState('ready');
    }
  };

  const signOut = async () => {
    try {
      if (getToken()) await api.logout();
    } catch {
      // Local sign-out must still complete if the server is temporarily unreachable.
    } finally {
      setToken(null);
      setUser(null);
      setProducts([]);
      setOrders([]);
      setDeskOrders([]);
      setExportBatches([]);
      setVanData(null);
      setInactivityData(null);
      setCart({});
      setCartPreview(null);
      showScreen('login');
    }
  };

  const updateCart = (product: Product, change: number) => {
    setCart((current) => {
      const next = Math.min(
        product.available_cases,
        Math.max(0, (current[product.id] ?? 0) + change),
      );
      if (next === 0) {
        const remaining = { ...current };
        delete remaining[product.id];
        return remaining;
      }
      return { ...current, [product.id]: next };
    });
    setCartPreview(null);
    setNotice('');
  };

  const reviewCart = async () => {
    if (!cartItems.length) return;
    setBusy(true);
    setError('');
    try {
      const preview = await api.previewOrder(
        cartItems.map(({ product, quantity }) => ({
          product_id: product.id,
          quantity_cases: quantity,
        })),
      );
      setCartPreview(preview);
    } catch (previewError) {
      setError(errorMessage(previewError));
      setCartPreview(null);
    } finally {
      setBusy(false);
    }
  };

  const syncOfflineOrders = async () => {
    if (!offlineQueue.length) return;
    if (!navigator.onLine) {
      setError('Cannot sync while offline. Please connect to internet first.');
      return;
    }
    setBusy(true);
    setError('');
    const remaining: OfflineOrder[] = [];
    let synced = 0;
    for (const item of offlineQueue) {
      try {
        await api.placeOrder(
          item.items.map((i) => ({ product_id: i.productId, quantity_cases: i.quantity })),
          item.deliveryNotes,
          item.clientOrderId,
        );
        synced++;
      } catch (err) {
        remaining.push({ ...item, status: 'SYNC_FAILED', error: errorMessage(err) });
      }
    }
    setOfflineQueue(remaining);
    setBusy(false);
    if (synced > 0) {
      setNotice(`Successfully synced ${synced} offline order(s) to server.`);
      await loadRetailerData();
    }
    if (remaining.length > 0) {
      setError(`${remaining.length} offline order(s) failed sync due to server validation/stock constraints.`);
    }
  };

  const submitOrder = async () => {
    if (!cartItems.length) return;
    setBusy(true);
    setError('');

    // Offline salesman queueing
    if (!navigator.onLine) {
      const clientOrderId = crypto.randomUUID();
      const offlineItem: OfflineOrder = {
        clientOrderId,
        items: cartItems.map(({ product, quantity }) => ({
          productId: product.id,
          productName: product.name,
          quantity,
        })),
        deliveryNotes,
        createdAt: new Date().toISOString(),
        status: 'PENDING_SYNC',
      };
      setOfflineQueue((prev) => [...prev, offlineItem]);
      setNotice(`Offline order queued (Client ID: ${clientOrderId.slice(0, 8)}). Will sync when connection is restored.`);
      setCart({});
      setCartPreview(null);
      setDeliveryNotes('');
      showScreen('orders');
      setBusy(false);
      return;
    }

    try {
      const submitted = await api.placeOrder(
        cartItems.map(({ product, quantity }) => ({
          product_id: product.id,
          quantity_cases: quantity,
        })),
        deliveryNotes,
      );
      setNotice(`Order ${submitted.order_number} submitted · ${submitted.status.replace(/_/g, ' ')}`);
      setCart({});
      setCartPreview(null);
      setDeliveryNotes('');
      setSelectedOrder(submitted);
      showScreen('orders');
      await loadRetailerData();
    } catch (submitError) {
      setError(errorMessage(submitError));
      if (errorMessage(submitError).toLowerCase().includes('stock')) {
        setCartPreview(null);
        await loadRetailerData();
      }
    } finally {
      setBusy(false);
    }
  };

  const capturePhotoOrder = async () => {
    if (!photoFile) {
      setError('Please select or capture a photo of the handwritten order slip first.');
      return;
    }
    const validImageTypes = ['image/jpeg', 'image/png', 'image/webp', 'image/jpg'];
    if (!validImageTypes.includes(photoFile.type.toLowerCase()) && !/\.(jpe?g|png|webp)$/i.test(photoFile.name)) {
      setError('Unsupported file type. Please upload a clear photo of your handwritten slip in JPEG, PNG, or WebP format.');
      return;
    }
    setBusy(true);
    setError('');
    setCapture(null);
    setReviewedLines([]);
    try {
      const result = await api.capturePhoto(photoFile);
      if (!result.lines || result.lines.length === 0) {
        const noLinesMsg = 'Your upload is incorrect. No grocery items could be recognized in this photo. Please make sure the handwriting is clear and well-lit, then try again.';
        setError(noLinesMsg);
        setUploadErrorModal({
          mode: 'photo',
          title: 'Incorrect Order Photo',
          message: noLinesMsg,
        });
        return;
      }
      setCapture(result);
      setCaptureResolution(Object.fromEntries(result.lines.map((line) => [
        line.id,
        {
          productId: line.resolved_product_id || line.matched_product_id || '',
          quantity: line.resolved_quantity || line.parsed_quantity,
          unit: line.unit_clarification_needed
            ? ''
            : line.parsed_uom.toUpperCase() === 'PIECE' ? 'PIECE' : 'CASE',
          saveAlias: false,
        },
      ])));
      setNotice('Handwritten order image processed! Review each SKU, quantity, and unit before adding to cart.');
    } catch (photoError) {
      const msg = errorMessage(photoError);
      const cleanMsg = msg && !msg.startsWith('Request failed (500)')
        ? msg
        : 'Your upload is incorrect. The uploaded photo is not a valid grocery order slip. Please upload a clear photo of your handwritten grocery order.';
      setError(cleanMsg);
      setUploadErrorModal({
        mode: 'photo',
        title: 'Incorrect Order Slip Photo',
        message: cleanMsg,
      });
    } finally {
      setBusy(false);
    }
  };

  const startVoiceRecording = async () => {
    try {
      const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
      audioChunksRef.current = [];
      const mediaRecorder = new MediaRecorder(stream);
      mediaRecorderRef.current = mediaRecorder;

      mediaRecorder.ondataavailable = (event) => {
        if (event.data.size > 0) audioChunksRef.current.push(event.data);
      };

      mediaRecorder.onstop = () => {
        const audioBlob = new Blob(audioChunksRef.current, { type: 'audio/webm' });
        const file = new File([audioBlob], 'voice-order.webm', { type: 'audio/webm' });
        setVoiceFile(file);
        stream.getTracks().forEach((track) => track.stop());
      };

      mediaRecorder.start();
      setIsRecording(true);
    } catch (err) {
      setError('Microphone access denied or unsupported in this browser: ' + errorMessage(err));
    }
  };

  const stopVoiceRecording = () => {
    if (mediaRecorderRef.current && isRecording) {
      mediaRecorderRef.current.stop();
      setIsRecording(false);
    }
  };

  const captureVoiceOrder = async () => {
    if (!voiceFile) {
      setError('Please record or select an audio recording first.');
      return;
    }
    const validAudioExts = ['.webm', '.mp3', '.wav', '.ogg', '.m4a'];
    const isAudio = voiceFile.type.startsWith('audio/') || validAudioExts.some((ext) => voiceFile.name.toLowerCase().endsWith(ext));
    if (!isAudio) {
      setError('Unsupported audio file. Please record or upload an audio note in MP3, WAV, WebM, or M4A format.');
      return;
    }
    setBusy(true);
    setError('');
    setCapture(null);
    setReviewedLines([]);
    try {
      const result = await api.captureVoice(voiceFile);
      if (!result.lines || result.lines.length === 0) {
        const noLinesMsg = 'Your upload is incorrect. No order items could be recognized in this audio. Please speak clearly (e.g. "bhaiya 5 peti biscuit, 2 peti detergent") and try again.';
        setError(noLinesMsg);
        setUploadErrorModal({
          mode: 'voice',
          title: 'Voice Note Not Recognized',
          message: noLinesMsg,
        });
        return;
      }
      setCapture(result);
      setCaptureResolution(Object.fromEntries(result.lines.map((line) => [
        line.id,
        {
          productId: line.resolved_product_id || line.matched_product_id || '',
          quantity: line.resolved_quantity || line.parsed_quantity,
          unit: line.unit_clarification_needed
            ? ''
            : line.parsed_uom.toUpperCase() === 'PIECE' ? 'PIECE' : 'CASE',
          saveAlias: false,
        },
      ])));
      setNotice('Hindi/Hinglish audio transcribed & processed! Please review each detected line.');
    } catch (voiceError) {
      const msg = errorMessage(voiceError);
      const cleanMsg = msg && !msg.startsWith('Request failed (500)')
        ? msg
        : 'Your upload is incorrect. No grocery order items could be recognized in this audio. Please record a clear voice note with product names and quantities.';
      setError(cleanMsg);
      setUploadErrorModal({
        mode: 'voice',
        title: 'Voice Note Not Recognized',
        message: cleanMsg,
      });
    } finally {
      setBusy(false);
    }
  };

  const openRepeatOrder = async (order: OrderRecord) => {
    setBusy(true);
    setError('');
    setRepeatSourceOrder(order);
    try {
      const preview = await api.repeatOrderPreview(order.id);
      setRepeatPreview(preview);
    } catch (repeatErr) {
      setError(errorMessage(repeatErr));
    } finally {
      setBusy(false);
    }
  };

  const confirmRepeatToCart = () => {
    if (!repeatPreview || !repeatPreview.can_repeat) return;
    const nextCart: Record<string, number> = {};
    repeatPreview.lines.forEach((line) => {
      if (!line.is_out_of_stock && line.new_qty > 0) {
        nextCart[line.product_id] = line.new_qty;
      }
    });
    setCart(nextCart);
    setRepeatPreview(null);
    setRepeatSourceOrder(null);
    showScreen('cart');
    setNotice('Loaded items from previous order into cart with live pricing and current schemes. Review cart to proceed.');
  };

  const captureMessage = async () => {
    if (rawMessage.trim().length < 3) {
      setError('Enter an order message with at least 3 characters.');
      return;
    }
    setBusy(true);
    setError('');
    setCapture(null);
    setReviewedLines([]);
    try {
      const result = await api.captureText(rawMessage.trim());
      setCapture(result);
      setCaptureResolution(Object.fromEntries(result.lines.map((line) => [
        line.id,
        {
          productId: line.resolved_product_id || line.matched_product_id || '',
          quantity: line.resolved_quantity || line.parsed_quantity,
          unit: line.unit_clarification_needed
            ? ''
            : line.parsed_uom.toUpperCase() === 'PIECE' ? 'PIECE' : 'CASE',
          saveAlias: false,
        },
      ])));
      setNotice(result.is_ai_fallback
        ? 'AI provider unavailable; the backend local parser made these suggestions. Review every line before adding it to your cart.'
        : 'Review each suggested SKU and quantity. Nothing is ordered until you confirm.');
    } catch (captureError) {
      setError(errorMessage(captureError));
    } finally {
      setBusy(false);
    }
  };

  const updateResolution = (lineId: string, patch: Partial<CaptureResolution>) => {
    setCaptureResolution((current) => ({
      ...current,
      [lineId]: { ...current[lineId], ...patch },
    }));
    setReviewedLines((current) => current.filter((id) => id !== lineId));
  };

  const reviewLine = async (line: CaptureLine) => {
    if (!capture) return;
    const resolution = captureResolution[line.id];
    if (!resolution?.productId || !resolution.quantity || !resolution.unit) return;
    setBusy(true);
    setError('');
    try {
      const updatedLine = await api.reviewCaptureLine(capture.id, line.id, {
        resolved_product_id: resolution.productId,
        resolved_quantity: resolution.quantity,
        resolved_uom: resolution.unit,
        is_confirmed: true,
        save_as_retailer_alias: resolution.saveAlias,
        alias_phrase: line.parsed_item_name,
      });
      setCapture((current) => current && ({
        ...current,
        lines: current.lines.map((item) => item.id === line.id ? updatedLine : item),
      }));
      setReviewedLines((current) => current.includes(line.id) ? current : [...current, line.id]);
      setNotice(resolution.unit === 'PIECE'
        ? 'Piece-based ordering is currently unsupported. This line cannot be added to checkout; choose cases or remove the line.'
        : 'Line reviewed and saved.');
    } catch (reviewError) {
      setError(errorMessage(reviewError));
    } finally {
      setBusy(false);
    }
  };

  const addCaptureToCart = async () => {
    if (!capture || reviewedLines.length !== capture.lines.length) return;
    setBusy(true);
    setError('');
    try {
      const confirmed = await api.confirmCapture(capture.id);
      const nextCart: Record<string, number> = {};
      confirmed.order_preview.lines.forEach((line) => {
        nextCart[line.product_id] = (nextCart[line.product_id] ?? 0) + line.requested_qty;
      });
      setCart(nextCart);
      setCartPreview(confirmed.order_preview);
      showScreen('cart');
      setNotice(`${confirmed.confirmed_lines_count} reviewed lines added to cart. Check stock, scheme, and credit before placing the order.`);
    } catch (confirmError) {
      setError(errorMessage(confirmError));
    } finally {
      setBusy(false);
    }
  };

  const refreshDeskOrders = async () => {
    const result = await api.deskOrders(orderFilter === 'All' ? undefined : orderFilter);
    setDeskOrders(result.items);
  };

  const openDeskOrder = async (order: OrderRecord) => {
    setBusy(true);
    setError('');
    try {
      setSelectedDeskOrder(await api.deskOrderDetail(order.id));
    } catch (detailError) {
      setError(errorMessage(detailError));
    } finally {
      setBusy(false);
    }
  };

  const approveDeskOrder = async (order: OrderRecord) => {
    const override = order.status === 'CREDIT_HOLD';
    if (override && !window.confirm('This order is on credit hold. Approve anyway and override the hold?')) return;
    setBusy(true);
    setError('');
    try {
      const approved = await api.approveOrder(order.id, override);
      setSelectedDeskOrder(approved);
      setNotice(`${approved.order_number} approved.`);
      await loadDeskData();
    } catch (approvalError) {
      setError(errorMessage(approvalError));
    } finally {
      setBusy(false);
    }
  };

  const holdDeskOrder = async (order: OrderRecord) => {
    const reason = window.prompt('Reason for placing this order on hold:');
    if (!reason?.trim()) return;
    setBusy(true);
    setError('');
    try {
      const held = await api.holdOrder(order.id, reason.trim());
      setSelectedDeskOrder(held);
      setNotice(`${held.order_number} placed on hold.`);
      await loadDeskData();
    } catch (holdError) {
      setError(errorMessage(holdError));
    } finally {
      setBusy(false);
    }
  };

  const generateExport = async () => {
    setBusy(true);
    setError('');
    try {
      const batch = await api.createExport(selectedExportOrders.length ? selectedExportOrders : undefined);
      setNotice(`${batch.file_name} generated for ${batch.order_count} approved order(s).`);
      setSelectedExportOrders([]);
      await loadDeskData();
    } catch (exportError) {
      setError(errorMessage(exportError));
    } finally {
      setBusy(false);
    }
  };

  const downloadBatch = async (batch: ExportBatch) => {
    setBusy(true);
    setError('');
    try {
      const blob = await api.downloadExport(batch.download_url);
      const objectUrl = URL.createObjectURL(blob);
      const anchor = document.createElement('a');
      anchor.href = objectUrl;
      anchor.download = batch.file_name;
      anchor.click();
      URL.revokeObjectURL(objectUrl);
    } catch (downloadError) {
      setError(errorMessage(downloadError));
    } finally {
      setBusy(false);
    }
  };

  const fetchRetailerOrderDetails = async (order: OrderRecord) => {
    setSelectedOrder((current) => current?.id === order.id ? null : order);
    if (order.items) return;
    try {
      setSelectedOrder(await api.retailerOrderDetail(order.id));
    } catch (detailError) {
      setError(errorMessage(detailError));
    }
  };

  if (loginState === 'loading') {
    return <div className="flex min-h-screen items-center justify-center bg-[#f6f8f6] text-emerald-800"><LoaderCircle className="mr-3 h-5 w-5 animate-spin" /> Restoring secure session…</div>;
  }

  if (!user || screen === 'login') {
    const redirectParam = typeof window !== 'undefined' ? new URLSearchParams(window.location.search).get('redirect') : null;
    return (
      <div className="login-shell min-h-screen bg-[#f4f7f4] px-4 py-8">
        <div className="mx-auto grid min-h-[calc(100vh-4rem)] max-w-6xl overflow-hidden rounded-[30px] border border-emerald-950/10 bg-white shadow-[0_35px_80px_-35px_rgba(13,71,50,.3)] lg:grid-cols-[1.05fr_.95fr]">
          <div className="login-visual relative hidden flex-col justify-between overflow-hidden bg-[#0b4a36] p-10 text-white lg:flex">
            <div className="flex items-center gap-3">
              <span className="flex h-12 w-12 items-center justify-center rounded-2xl bg-white font-black text-[#0b4a36]">VS</span>
              <div><div className="text-xl font-extrabold">VyapaarSetu</div><div className="text-xs text-emerald-100">Grow Together</div></div>
            </div>
            <div className="relative z-10 max-w-md">
              <div className="mb-5 inline-flex items-center gap-2 rounded-full border border-white/15 bg-white/10 px-3 py-1.5 text-xs font-semibold text-emerald-100"><Sparkles className="h-3.5 w-3.5" /> Ordering, made simpler</div>
              <h1 className="text-5xl font-extrabold leading-[1.08] tracking-[-.05em]">Your next order, in a minute.</h1>
              <p className="mt-5 max-w-sm text-base leading-7 text-emerald-50/80">Live stock, your dealer pricing, and current schemes in one easy place.</p>
            </div>
            <div className="relative z-10 flex items-center gap-3 rounded-2xl border border-white/10 bg-white/[.07] p-4">
              <div className="flex h-11 w-11 items-center justify-center rounded-xl bg-emerald-300/15"><Truck className="h-5 w-5 text-emerald-200" /></div>
              <div><div className="text-sm font-bold">Jabalpur, Madhya Pradesh</div><div className="text-xs text-emerald-100/70">A better link from distributor to retailer</div></div>
            </div>
            <div className="login-orbit login-orbit-one" /><div className="login-orbit login-orbit-two" />
          </div>
          <div className="flex items-center justify-center p-6 sm:p-10 lg:p-14">
            <div className="w-full max-w-md">
              <div className="mb-9 flex items-center gap-3 lg:hidden">
                <span className="flex h-11 w-11 items-center justify-center rounded-xl bg-[#0b4a36] font-black text-white">VS</span>
                <div><div className="text-xl font-extrabold text-slate-900">VyapaarSetu</div><div className="text-xs text-slate-500">Grow Together</div></div>
              </div>

              {user && (
                <div className="mb-6 rounded-2xl border border-emerald-200 bg-emerald-50/90 p-4">
                  <div className="flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
                    <div>
                      <p className="text-xs font-semibold text-emerald-800">Currently signed in as:</p>
                      <p className="text-sm font-extrabold text-emerald-950">
                        {user.retailer?.store_name ?? user.full_name} ({user.role === 'ROLE_ORDER_DESK' ? 'Order Desk' : 'Retailer'})
                      </p>
                    </div>
                    <div className="flex items-center gap-2">
                      <button
                        type="button"
                        onClick={() => showScreen(user.role === 'ROLE_ORDER_DESK' ? 'desk' : 'catalogue')}
                        className="rounded-xl bg-emerald-700 px-3.5 py-2 text-xs font-bold text-white shadow-sm hover:bg-emerald-800"
                      >
                        Open {user.role === 'ROLE_ORDER_DESK' ? 'Order Desk' : 'Catalogue'}
                      </button>
                      <button
                        type="button"
                        onClick={signOut}
                        className="rounded-xl border border-emerald-300 bg-white px-3 py-2 text-xs font-semibold text-emerald-800 hover:bg-emerald-100"
                      >
                        Sign Out
                      </button>
                    </div>
                  </div>
                </div>
              )}

              {!user && redirectParam && redirectParam !== '/' && redirectParam !== '/catalogue' && redirectParam !== '/login' && (
                <div className="mb-5 rounded-xl border border-amber-200 bg-amber-50 p-3 text-xs font-semibold text-amber-800">
                  Please sign in to access <span className="font-bold underline">{redirectParam}</span>.
                </div>
              )}

              {/* Main Tab Switcher: Sign In vs Create Account */}
              <div className="mb-6 grid grid-cols-2 rounded-2xl bg-slate-100 p-1.5 border border-slate-200/80 shadow-inner">
                <button
                  type="button"
                  onClick={() => { setAuthTab('signin'); setError(''); setOtpNotice(''); setAccountNotFoundNotice(false); }}
                  className={`flex items-center justify-center gap-2 rounded-xl py-2.5 text-sm font-bold transition ${authTab === 'signin' ? 'bg-white text-emerald-900 shadow-sm' : 'text-slate-500 hover:text-slate-800'}`}
                >
                  <Smartphone className="h-4 w-4" />
                  Sign In
                </button>
                <button
                  type="button"
                  onClick={() => { setAuthTab('signup'); setError(''); setOtpNotice(''); setAccountNotFoundNotice(false); }}
                  className={`flex items-center justify-center gap-2 rounded-xl py-2.5 text-sm font-bold transition ${authTab === 'signup' ? 'bg-white text-emerald-900 shadow-sm' : 'text-slate-500 hover:text-slate-800'}`}
                >
                  <Store className="h-4 w-4" />
                  Create Account
                  <span className="rounded-full bg-emerald-100 px-1.5 py-0.5 text-[10px] font-extrabold text-emerald-800">New</span>
                </button>
              </div>

              {/* Title & Subtitle */}
              <div className="mb-6">
                <p className="text-xs font-bold uppercase tracking-[.18em] text-emerald-700">
                  {authTab === 'signin' ? 'Welcome Back' : 'New Kirana Registration'}
                </p>
                <h2 className="mt-1 text-2xl font-extrabold tracking-[-.03em] text-slate-900 sm:text-3xl">
                  {authTab === 'signin' ? 'Sign in to your account' : 'Register your Kirana Store'}
                </h2>
                <p className="mt-1.5 text-xs sm:text-sm leading-5 text-slate-500">
                  {authTab === 'signin'
                    ? 'Enter your mobile number and OTP to access live stock and orders.'
                    : 'Get ₹50,000 starter credit line, wholesale rates, and AI ordering.'}
                </p>
              </div>

              {/* 1-Click Instant Demo Login Cards */}
              <div className="mb-6 rounded-2xl border border-emerald-100 bg-emerald-50/70 p-3.5">
                <div className="mb-2 flex items-center justify-between">
                  <span className="flex items-center gap-1.5 text-xs font-bold text-emerald-900">
                    <Sparkles className="h-3.5 w-3.5 text-emerald-700" />
                    One-Click Quick Access
                  </span>
                  <span className="text-[10px] font-semibold text-emerald-700">Jabalpur FMCG</span>
                </div>
                <div className="grid gap-2 sm:grid-cols-2">
                  <button
                    type="button"
                    disabled={loginBusy}
                    onClick={() => void quickSignIn('retailer')}
                    className="tap-button flex items-center justify-between rounded-xl bg-white px-3 py-2.5 text-left shadow-xs border border-emerald-100 hover:border-emerald-300 transition"
                  >
                    <div>
                      <span className="block text-xs font-extrabold text-slate-800">Ramesh Patel</span>
                      <span className="block text-[10px] font-semibold text-emerald-700">Retailer (Patel Kirana)</span>
                    </div>
                    <ArrowRight className="h-3.5 w-3.5 text-slate-400" />
                  </button>
                  <button
                    type="button"
                    disabled={loginBusy}
                    onClick={() => void quickSignIn('desk')}
                    className="tap-button flex items-center justify-between rounded-xl bg-white px-3 py-2.5 text-left shadow-xs border border-emerald-100 hover:border-emerald-300 transition"
                  >
                    <div>
                      <span className="block text-xs font-extrabold text-slate-800">Sanjay Sharma</span>
                      <span className="block text-[10px] font-semibold text-emerald-700">Order Desk Supervisor</span>
                    </div>
                    <ArrowRight className="h-3.5 w-3.5 text-slate-400" />
                  </button>
                </div>
              </div>

              {/* OTP Sent Success Alert */}
              {otpNotice && (
                <div className="mb-5 flex items-start gap-2.5 rounded-xl border border-emerald-200 bg-emerald-50 p-3 text-xs font-medium text-emerald-900 shadow-xs">
                  <CheckCircle2 className="h-4 w-4 shrink-0 text-emerald-600 mt-0.5" />
                  <div className="flex-1 leading-5">{otpNotice}</div>
                </div>
              )}

              {/* Account Not Found Banner - Suggests Instant Registration */}
              {accountNotFoundNotice && (
                <div className="mb-5 rounded-2xl border border-amber-200 bg-amber-50 p-4 text-xs text-amber-900 shadow-xs">
                  <p className="font-bold text-amber-950">No Kirana account found with this mobile number.</p>
                  <p className="mt-1 text-amber-800">
                    Would you like to register as a new Kirana store? It only takes 30 seconds to get your ₹50,000 credit line.
                  </p>
                  <button
                    type="button"
                    onClick={() => {
                      setAuthTab('signup');
                      setSignUpForm((prev) => ({ ...prev, phone: loginForm.phone }));
                      setError('');
                      setAccountNotFoundNotice(false);
                    }}
                    className="mt-3 inline-flex items-center gap-1.5 rounded-xl bg-emerald-800 px-3.5 py-2 text-xs font-bold text-white shadow-xs hover:bg-emerald-900 transition"
                  >
                    <Store className="h-3.5 w-3.5" />
                    Register Kirana Account with {loginForm.phone}
                  </button>
                </div>
              )}

              {authTab === 'signin' ? (
                <>
                  <div className="mb-5 grid grid-cols-2 rounded-xl bg-slate-100 p-1">
                    {(['retailer', 'desk'] as const).map((role) => (
                      <button
                        type="button"
                        key={role}
                        onClick={() => { setLoginRole(role); setLoginForm(DEMO_ACCOUNTS[role]); setError(''); setOtpNotice(''); setAccountNotFoundNotice(false); }}
                        className={`rounded-lg px-3 py-2.5 text-xs font-bold transition ${loginRole === role ? 'bg-white text-emerald-800 shadow-sm' : 'text-slate-500 hover:text-slate-800'}`}
                      >
                        {role === 'retailer' ? 'Retailer Portal' : 'Order Desk Portal'}
                      </button>
                    ))}
                  </div>

                  <form onSubmit={signIn} className="space-y-4">
                    <div>
                      <div className="flex items-center justify-between">
                        <label className="block text-xs font-bold uppercase tracking-wider text-slate-700">Mobile number</label>
                        <button
                          type="button"
                          disabled={sendingOtp || otpTimer > 0}
                          onClick={() => void handleSendOtp(loginForm.phone)}
                          className="text-xs font-bold text-emerald-700 hover:text-emerald-900 hover:underline disabled:opacity-60 disabled:hover:no-underline"
                        >
                          {sendingOtp ? 'Sending…' : otpTimer > 0 ? `Resend OTP in ${otpTimer}s` : 'Send OTP'}
                        </button>
                      </div>
                      <div className="mt-1.5 flex rounded-xl border border-slate-200 bg-white focus-within:border-emerald-500 focus-within:ring-4 focus-within:ring-emerald-50">
                        <span className="flex items-center border-r border-slate-200 px-3 text-sm font-semibold text-slate-600 bg-slate-50 rounded-l-xl">+91</span>
                        <input
                          value={loginForm.phone}
                          onChange={(event) => setLoginForm({ ...loginForm, phone: event.target.value })}
                          inputMode="tel"
                          autoComplete="tel"
                          placeholder="e.g. 9826011111"
                          required
                          className="min-w-0 flex-1 rounded-r-xl px-3 py-3 text-sm outline-none"
                        />
                      </div>
                    </div>

                    <div>
                      <div className="flex items-center justify-between">
                        <label className="block text-xs font-bold uppercase tracking-wider text-slate-700">One-time password (OTP)</label>
                        <span className="text-[11px] text-slate-400">Dev code: 123456</span>
                      </div>
                      <div className="mt-1.5 relative flex items-center rounded-xl border border-slate-200 bg-white focus-within:border-emerald-500 focus-within:ring-4 focus-within:ring-emerald-50">
                        <KeyRound className="absolute left-3.5 h-4 w-4 text-slate-400" />
                        <input
                          value={loginForm.otp}
                          onChange={(event) => setLoginForm({ ...loginForm, otp: event.target.value })}
                          inputMode="numeric"
                          autoComplete="one-time-code"
                          placeholder="6-digit code"
                          required
                          className="w-full rounded-xl pl-10 pr-4 py-3 text-sm tracking-[.2em] outline-none"
                        />
                      </div>
                    </div>

                    {error && <ErrorBanner message={error} />}

                    <button
                      type="submit"
                      disabled={loginBusy}
                      className="flex w-full items-center justify-center gap-2 rounded-xl bg-[#0d5a40] px-4 py-3.5 text-sm font-bold text-white shadow-sm transition hover:bg-[#094a35] disabled:cursor-wait disabled:opacity-70"
                    >
                      {loginBusy ? <LoaderCircle className="h-4 w-4 animate-spin" /> : <ArrowRight className="h-4 w-4" />}
                      {loginBusy ? 'Signing in…' : `Continue as ${loginRole === 'retailer' ? 'Retailer' : 'Order Desk'}`}
                    </button>
                  </form>
                </>
              ) : (
                /* CREATE ACCOUNT (SIGN UP) FORM */
                <form onSubmit={signUp} className="space-y-4">
                  <div className="grid gap-3 sm:grid-cols-2">
                    <div>
                      <label className="block text-xs font-bold uppercase tracking-wider text-slate-700">Owner Full Name</label>
                      <div className="mt-1.5 relative flex items-center rounded-xl border border-slate-200 bg-white focus-within:border-emerald-500 focus-within:ring-4 focus-within:ring-emerald-50">
                        <UserRound className="absolute left-3 h-4 w-4 text-slate-400" />
                        <input
                          value={signUpForm.fullName}
                          onChange={(e) => setSignUpForm({ ...signUpForm, fullName: e.target.value })}
                          placeholder="e.g. Rajesh Kumar"
                          required
                          className="w-full rounded-xl pl-9 pr-3 py-2.5 text-sm outline-none"
                        />
                      </div>
                    </div>

                    <div>
                      <label className="block text-xs font-bold uppercase tracking-wider text-slate-700">Kirana / Shop Name</label>
                      <div className="mt-1.5 relative flex items-center rounded-xl border border-slate-200 bg-white focus-within:border-emerald-500 focus-within:ring-4 focus-within:ring-emerald-50">
                        <Store className="absolute left-3 h-4 w-4 text-slate-400" />
                        <input
                          value={signUpForm.storeName}
                          onChange={(e) => setSignUpForm({ ...signUpForm, storeName: e.target.value })}
                          placeholder="e.g. Kumar General Store"
                          required
                          className="w-full rounded-xl pl-9 pr-3 py-2.5 text-sm outline-none"
                        />
                      </div>
                    </div>
                  </div>

                  <div>
                    <div className="flex items-center justify-between">
                      <label className="block text-xs font-bold uppercase tracking-wider text-slate-700">Mobile Number</label>
                      <button
                        type="button"
                        disabled={sendingOtp || otpTimer > 0}
                        onClick={() => void handleSendOtp(signUpForm.phone)}
                        className="text-xs font-bold text-emerald-700 hover:text-emerald-900 hover:underline disabled:opacity-60 disabled:hover:no-underline"
                      >
                        {sendingOtp ? 'Sending…' : otpTimer > 0 ? `Resend in ${otpTimer}s` : 'Get OTP'}
                      </button>
                    </div>
                    <div className="mt-1.5 flex rounded-xl border border-slate-200 bg-white focus-within:border-emerald-500 focus-within:ring-4 focus-within:ring-emerald-50">
                      <span className="flex items-center border-r border-slate-200 px-3 text-sm font-semibold text-slate-600 bg-slate-50 rounded-l-xl">+91</span>
                      <input
                        value={signUpForm.phone}
                        onChange={(e) => setSignUpForm({ ...signUpForm, phone: e.target.value })}
                        inputMode="tel"
                        autoComplete="tel"
                        placeholder="e.g. 9876543210"
                        required
                        className="min-w-0 flex-1 rounded-r-xl px-3 py-2.5 text-sm outline-none"
                      />
                    </div>
                  </div>

                  <div className="grid gap-3 sm:grid-cols-2">
                    <div>
                      <label className="block text-xs font-bold uppercase tracking-wider text-slate-700">City</label>
                      <div className="mt-1.5 relative flex items-center rounded-xl border border-slate-200 bg-white focus-within:border-emerald-500 focus-within:ring-4 focus-within:ring-emerald-50">
                        <MapPin className="absolute left-3 h-4 w-4 text-slate-400" />
                        <input
                          value={signUpForm.city}
                          onChange={(e) => setSignUpForm({ ...signUpForm, city: e.target.value })}
                          placeholder="Jabalpur"
                          required
                          className="w-full rounded-xl pl-9 pr-3 py-2.5 text-sm outline-none"
                        />
                      </div>
                    </div>

                    <div>
                      <label className="block text-xs font-bold uppercase tracking-wider text-slate-700">GSTIN <span className="text-[10px] text-slate-400 font-normal">(Optional)</span></label>
                      <div className="mt-1.5 relative flex items-center rounded-xl border border-slate-200 bg-white focus-within:border-emerald-500 focus-within:ring-4 focus-within:ring-emerald-50">
                        <Building2 className="absolute left-3 h-4 w-4 text-slate-400" />
                        <input
                          value={signUpForm.gstNumber}
                          onChange={(e) => setSignUpForm({ ...signUpForm, gstNumber: e.target.value })}
                          placeholder="23AAAAA0000A1Z5"
                          className="w-full rounded-xl pl-9 pr-3 py-2.5 text-sm outline-none"
                        />
                      </div>
                    </div>
                  </div>

                  <div>
                    <label className="block text-xs font-bold uppercase tracking-wider text-slate-700">Shop Address / Landmark</label>
                    <input
                      value={signUpForm.address}
                      onChange={(e) => setSignUpForm({ ...signUpForm, address: e.target.value })}
                      placeholder="Shop No. 4, Main Road, Wright Town, Jabalpur"
                      className="mt-1.5 w-full rounded-xl border border-slate-200 px-3.5 py-2.5 text-sm outline-none focus:border-emerald-500 focus:ring-4 focus:ring-emerald-50"
                    />
                  </div>

                  <div>
                    <div className="flex items-center justify-between">
                      <label className="block text-xs font-bold uppercase tracking-wider text-slate-700">Enter OTP Code</label>
                      <span className="text-[11px] text-slate-400">Default code: 123456</span>
                    </div>
                    <div className="mt-1.5 relative flex items-center rounded-xl border border-slate-200 bg-white focus-within:border-emerald-500 focus-within:ring-4 focus-within:ring-emerald-50">
                      <KeyRound className="absolute left-3.5 h-4 w-4 text-slate-400" />
                      <input
                        value={signUpForm.otp}
                        onChange={(e) => setSignUpForm({ ...signUpForm, otp: e.target.value })}
                        inputMode="numeric"
                        placeholder="6-digit OTP code"
                        required
                        className="w-full rounded-xl pl-10 pr-4 py-2.5 text-sm tracking-[.2em] outline-none"
                      />
                    </div>
                  </div>

                  {error && <ErrorBanner message={error} />}

                  <button
                    type="submit"
                    disabled={loginBusy}
                    className="flex w-full items-center justify-center gap-2 rounded-xl bg-[#0d5a40] px-4 py-3.5 text-sm font-bold text-white shadow-sm transition hover:bg-[#094a35] disabled:cursor-wait disabled:opacity-70"
                  >
                    {loginBusy ? <LoaderCircle className="h-4 w-4 animate-spin" /> : <CheckCircle2 className="h-4 w-4" />}
                    {loginBusy ? 'Creating Kirana Account…' : 'Register & Start Ordering (₹50k Credit)'}
                  </button>
                  <p className="text-center text-[11px] text-slate-500">
                    Starter credit line ₹50,000 allocated immediately upon OTP verification.
                  </p>
                </form>
              )}

              <div className="mt-6 flex items-start gap-2 rounded-xl bg-slate-50 p-3 text-xs leading-5 text-slate-500">
                <CircleHelp className="mt-0.5 h-4 w-4 shrink-0 text-emerald-700" />
                <span>
                  Demo quick credentials: Retailer <b>9826011111</b>, Order Desk <b>9826000000</b>. OTP: <b>123456</b>. Any new number can register via OTP.
                </span>
              </div>
            </div>
          </div>
        </div>
      </div>
    );
  }

  const role: LoginRole = user.role === 'ROLE_ORDER_DESK' ? 'desk' : 'retailer';
  const retailer = user.retailer;
  const retailerName = retailer?.store_name ?? user.full_name;
  const titleMap: Record<Screen, string> = {
    login: 'Sign in',
    catalogue: 'Catalogue',
    cart: 'Your cart',
    ai: 'AI order capture',
    orders: 'My orders',
    desk: 'Order desk',
    van: 'Van loading list',
    inactivity: 'Retailer inactivity',
    exports: 'Tally export',
    account: 'Account',
  };

  const renderProductCard = (product: Product) => {
    const quantity = cart[product.id] ?? 0;
    const stock = stockLabel(product.available_cases);
    const tone = stock.tone === 'green' ? 'bg-emerald-50 text-emerald-700' : stock.tone === 'amber' ? 'bg-amber-50 text-amber-700' : 'bg-rose-50 text-rose-700';
    const scheme = product.active_schemes?.[0];
    const basis = product.price_basis === 'PER_CASE' ? 'per case' : product.price_basis === 'PER_PIECE' ? 'per piece' : 'price unit pending';
    return (
      <article key={product.id} className="product-card flex flex-col rounded-[22px] border border-slate-200/90 bg-white p-3.5 shadow-[0_2px_8px_rgba(15,23,42,.035)] transition hover:-translate-y-0.5 hover:shadow-[0_18px_36px_-18px_rgba(15,23,42,.24)] sm:p-4">
        <div className="mb-2 flex items-center justify-between">
          <span className={`rounded-full px-2.5 py-1 text-[11px] font-bold ${tone}`}><span className="mr-1.5 inline-block h-1.5 w-1.5 rounded-full bg-current align-middle" />{stock.text}</span>
          <span className="max-w-[54%] truncate text-[10px] font-medium text-slate-400">{product.sku_code}</span>
        </div>
        <div className="product-image-stage flex h-[168px] items-center justify-center rounded-2xl bg-[#fbfcfb] sm:h-[184px]">
          <img
            src={product.image_url}
            alt={product.name}
            loading="lazy"
            className="h-full w-full object-contain p-2"
            onError={(event) => { event.currentTarget.src = '/images/products/placeholder.svg'; }}
          />
        </div>
        <div className="mt-3 flex-1">
          <span className="rounded-full bg-slate-100 px-2 py-1 text-[10px] font-semibold text-slate-600">{product.category}</span>
          <h3 className="mt-2 text-base font-extrabold leading-snug tracking-[-.02em] text-slate-900">{product.name}</h3>
          <p className="mt-1 text-xs text-slate-500">SKU: {product.sku_code} <span className="px-1 text-slate-300">|</span> Case of {product.units_per_case}</p>
          <div className="mt-3 flex items-baseline gap-1.5">
            <span className="text-[22px] font-extrabold tracking-tight text-slate-900">{formatMoney(product.effective_price ?? product.default_dealer_price)}</span>
            <span className="text-[11px] font-medium text-slate-500">Excl. GST</span>
          </div>
          <p className="mt-0.5 text-[10px] text-slate-400">{basis} · provisional price basis</p>
        </div>
        <div className="mt-3 min-h-[38px]">
          {scheme ? (
            <div className="flex min-h-[38px] items-center gap-2 rounded-lg bg-emerald-50 px-2.5 py-2 text-xs font-semibold leading-4 text-emerald-800">
              <BadgeCheck className="h-4 w-4 shrink-0 text-emerald-600" />{scheme.name}
            </div>
          ) : <div className="flex min-h-[38px] items-center gap-2 rounded-lg bg-slate-50 px-2.5 py-2 text-xs text-slate-500"><CircleHelp className="h-4 w-4" />No active scheme</div>}
        </div>
        <div className="mt-2 flex items-center justify-between text-xs text-slate-600">
          <span className="flex items-center gap-1.5"><Package className="h-3.5 w-3.5 text-emerald-700" />{product.available_cases} cases available</span>
        </div>
        <div className="mt-3 flex items-center gap-2">
          <div className="flex h-10 items-center rounded-xl border border-slate-200 bg-slate-50 p-1">
            <button disabled={!quantity} aria-label={`Remove one ${product.name}`} onClick={() => updateCart(product, -1)} className="tap-button flex h-8 w-8 items-center justify-center rounded-lg text-slate-600 hover:bg-white disabled:opacity-40"><Minus className="h-3.5 w-3.5" /></button>
            <span className="min-w-7 text-center text-sm font-bold text-slate-800">{quantity}</span>
            <button disabled={quantity >= product.available_cases} aria-label={`Add one ${product.name}`} onClick={() => updateCart(product, 1)} className="tap-button flex h-8 w-8 items-center justify-center rounded-lg text-slate-600 hover:bg-white disabled:opacity-40"><Plus className="h-3.5 w-3.5" /></button>
          </div>
          <button disabled={!product.available_cases} onClick={() => updateCart(product, 1)} className="tap-button flex h-10 flex-1 items-center justify-center gap-2 rounded-xl bg-[#0d5b40] px-3 text-xs font-bold text-white transition hover:bg-[#084a35] disabled:cursor-not-allowed disabled:bg-slate-200 disabled:text-slate-500">
            <ShoppingBag className="h-4 w-4" />{product.available_cases ? 'Add to cart' : 'Unavailable'}
          </button>
        </div>
      </article>
    );
  };

  const renderCatalogue = () => (
    <div className="space-y-5">
      <section className="catalogue-banner flex min-h-[188px] items-center justify-between overflow-hidden rounded-[24px] px-6 py-6 sm:px-8">
        <div className="relative z-10 max-w-[500px]">
          <span className="inline-flex items-center gap-1.5 rounded-full bg-white/75 px-3 py-1.5 text-[11px] font-bold text-emerald-800"><Sparkles className="h-3.5 w-3.5" /> SMART ORDERING</span>
          <h1 className="mt-3 text-[30px] font-extrabold leading-tight tracking-[-.045em] text-[#123f2f] sm:text-[36px]">Smart Order. Better Business.</h1>
          <p className="mt-2 max-w-md text-sm leading-6 text-[#315d49] sm:text-base">Get your dealer prices, current schemes and live stock — all in one place.</p>
          <button onClick={() => document.getElementById('catalogue-products')?.scrollIntoView({ behavior: 'smooth' })} className="mt-4 inline-flex items-center gap-2 rounded-xl bg-[#0d5b40] px-4 py-2.5 text-sm font-bold text-white shadow-sm hover:bg-[#084a35]">Start new order <ArrowRight className="h-4 w-4" /></button>
        </div>
        <div className="banner-products hidden items-end gap-2 pr-7 lg:flex">
          {products.slice(0, 3).map((product) => <img key={product.id} src={product.image_url} alt="" className="h-[138px] w-[100px] object-contain drop-shadow-lg" />)}
        </div>
        <div className="banner-leaf banner-leaf-one" /><div className="banner-leaf banner-leaf-two" />
      </section>

      <section className="grid gap-3 sm:grid-cols-2 xl:grid-cols-4">
        <MetricCard icon={CreditCard} title="Credit limit" amount={formatMoney(retailer?.credit_limit)} sub={`Available ${formatMoney(retailer?.available_credit)}`} tone="green" />
        <MetricCard icon={Store} title="Outstanding" amount={formatMoney(retailer?.outstanding_amount)} sub="Current ledger balance" tone="blue" />
        <MetricCard icon={BadgeCheck} title="Active schemes" amount={String(schemes.length)} sub="Across your catalogue" tone="purple" />
        <MetricCard icon={ShoppingBag} title="Recent orders" amount={String(orders.length)} sub="View order history" tone="amber" action={() => showScreen('orders')} />
      </section>

      <section id="catalogue-products" className="grid gap-4 xl:grid-cols-[228px_minmax(0,1fr)]">
        <aside className="h-fit rounded-[20px] border border-slate-200 bg-white p-4">
          <div className="flex items-center justify-between">
            <h2 className="flex items-center gap-2 text-sm font-extrabold text-slate-900"><Search className="h-4 w-4 text-slate-500" /> Filter products</h2>
            <button onClick={() => { setCategory('All'); setAvailability('All stock'); setQuery(''); }} className="text-xs font-bold text-emerald-700">Clear</button>
          </div>
          <div className="mt-5">
            <h3 className="mb-2 text-xs font-bold uppercase tracking-[.1em] text-slate-500">Category</h3>
            <div className="flex flex-wrap gap-1.5 xl:flex-col">
              {['All', ...Array.from(new Set(products.map((product) => product.category)))].map((item) => <button key={item} onClick={() => setCategory(item)} className={`rounded-full px-3 py-2 text-left text-xs font-semibold transition xl:rounded-lg ${category === item ? 'bg-[#0d5b40] text-white' : 'bg-slate-50 text-slate-600 hover:bg-emerald-50 hover:text-emerald-800'}`}>{item}</button>)}
            </div>
          </div>
          <div className="mt-5">
            <h3 className="mb-2 text-xs font-bold uppercase tracking-[.1em] text-slate-500">Availability</h3>
            <select value={availability} onChange={(event) => setAvailability(event.target.value)} className="w-full rounded-lg border border-slate-200 bg-white px-3 py-2.5 text-xs font-semibold text-slate-700 outline-none focus:border-emerald-400">
              {['All stock', 'In stock', 'Low stock', 'Out of stock'].map((item) => <option key={item}>{item}</option>)}
            </select>
          </div>
          <div className="mt-5 rounded-xl bg-[#fff7e9] p-3">
            <div className="flex items-center gap-2 text-xs font-extrabold text-amber-900"><Sparkles className="h-4 w-4 text-amber-600" /> Quick order</div>
            <p className="mt-1 text-[11px] leading-4 text-amber-800/80">Paste a WhatsApp order and review AI product matches.</p>
            <button onClick={() => showScreen('ai')} className="mt-2 inline-flex items-center gap-1 text-xs font-bold text-amber-800">Try AI capture <ArrowRight className="h-3.5 w-3.5" /></button>
          </div>
        </aside>

        <div className="min-w-0">
          <div className="mb-3 flex flex-wrap items-end justify-between gap-3">
            <div><p className="text-xs font-semibold text-slate-500">Your products and retailer pricing</p><h2 className="mt-1 text-[23px] font-extrabold tracking-[-.04em] text-slate-900">Our catalogue <span className="text-sm font-semibold text-slate-400">({filteredProducts.length})</span></h2></div>
            <div className="relative w-full sm:w-64"><Search className="absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-slate-400" /><input value={query} onChange={(event) => setQuery(event.target.value)} placeholder="Search products or SKU" className="w-full rounded-xl border border-slate-200 bg-white py-2.5 pl-9 pr-3 text-sm outline-none focus:border-emerald-400" /></div>
          </div>
          {dataLoading && !products.length ? <LoadingState label="Loading your catalogue and contracted prices…" /> :
            filteredProducts.length ? <div className="grid gap-3 sm:grid-cols-2 2xl:grid-cols-3">{filteredProducts.map(renderProductCard)}</div> :
              <EmptyState title="No products match these filters" action="Clear filters" onAction={() => { setQuery(''); setCategory('All'); setAvailability('All stock'); }} />}
        </div>
      </section>
    </div>
  );

  const renderCart = () => {
    const previewLines = cartPreview?.lines ?? [];
    return (
      <section className="grid gap-5 xl:grid-cols-[minmax(0,1fr)_340px]">
        <div className="rounded-[22px] border border-slate-200 bg-white p-4 sm:p-6">
          <div className="mb-5 flex items-center justify-between gap-3"><div><p className="text-xs font-bold uppercase tracking-[.16em] text-emerald-700">Checkout</p><h2 className="mt-1 text-2xl font-extrabold tracking-[-.04em] text-slate-900">Your cart <span className="text-base text-slate-400">({cartCount})</span></h2></div><button onClick={() => showScreen('catalogue')} className="text-sm font-bold text-emerald-700">Continue shopping</button></div>
          {cartItems.length === 0 ? <EmptyState title="Your cart is empty" message="Browse the catalogue and add available cases to get started." action="Go to catalogue" onAction={() => showScreen('catalogue')} /> :
            <div className="space-y-3">
              {cartItems.map(({ product, quantity }) => {
                const line = previewLines.find((item) => item.product_id === product.id);
                return <div key={product.id} className="flex items-center gap-3 rounded-2xl border border-slate-100 bg-slate-50/60 p-3 sm:gap-4 sm:p-4">
                  <img src={product.image_url} alt="" className="h-[72px] w-[68px] rounded-xl bg-white object-contain p-1" />
                  <div className="min-w-0 flex-1"><h3 className="truncate text-sm font-bold text-slate-900">{product.name}</h3><p className="mt-1 text-xs text-slate-500">{product.sku_code} · {formatMoney(line?.unit_price_excl_gst ?? product.effective_price)} excl. GST</p>
                    {line?.benefits && line.benefits.length > 0 ? (
                      <div className="mt-1.5 space-y-1 rounded-lg bg-emerald-50/70 p-2 border border-emerald-100">
                        <div className="text-[10px] font-bold uppercase tracking-wider text-emerald-800">Free Promotion Benefits</div>
                        {line.benefits.map((b) => (
                          <div key={b.id} className="flex items-center justify-between text-xs text-emerald-900">
                            <span>{b.free_product_name} <span className="text-emerald-600 font-mono text-[10px]">({b.free_sku_code})</span></span>
                            <span className="font-extrabold bg-emerald-200/80 px-1.5 py-0.5 rounded text-[10px]">+{b.free_qty} {b.free_uom} FREE</span>
                          </div>
                        ))}
                      </div>
                    ) : line?.applied_scheme_name ? (
                      <p className="mt-1 text-[11px] font-semibold text-emerald-700">{line.applied_scheme_name}{line.free_goods_qty > 0 ? ` · ${line.free_goods_qty} free case(s)` : ''}{Number(line.discount_amount_excl_gst) > 0 ? ` · ${formatMoney(line.discount_amount_excl_gst)} off` : ''}</p>
                    ) : null}
                    {line?.has_scheme_conflict && <p className="mt-1 text-[11px] font-semibold text-amber-700">{line.scheme_conflict_note || 'Scheme needs desk review.'}</p>}
                  </div>
                  <div className="flex items-center rounded-xl border border-slate-200 bg-white p-1"><button onClick={() => updateCart(product, -1)} className="tap-button flex h-8 w-8 items-center justify-center rounded-lg text-slate-600 hover:bg-slate-100"><Minus className="h-3.5 w-3.5" /></button><span className="w-7 text-center text-sm font-bold">{quantity}</span><button disabled={quantity >= product.available_cases} onClick={() => updateCart(product, 1)} className="tap-button flex h-8 w-8 items-center justify-center rounded-lg text-slate-600 hover:bg-slate-100 disabled:opacity-40"><Plus className="h-3.5 w-3.5" /></button></div>
                </div>;
              })}
            </div>}
          {cartItems.length > 0 && <label className="mt-5 block text-sm font-semibold text-slate-700">Delivery note <span className="font-normal text-slate-400">(optional)</span><textarea value={deliveryNotes} onChange={(event) => setDeliveryNotes(event.target.value)} placeholder="Any delivery instructions for the order desk?" rows={3} className="mt-2 w-full resize-y rounded-xl border border-slate-200 px-3 py-2.5 text-sm font-normal outline-none focus:border-emerald-400" /></label>}
        </div>
        <aside className="h-fit rounded-[22px] border border-slate-200 bg-white p-5">
          <h3 className="text-lg font-extrabold text-slate-900">Order summary</h3>
          {!cartPreview ? <div className="mt-4 rounded-xl bg-slate-50 p-3 text-xs leading-5 text-slate-600">Review this cart to calculate live schemes, stock, and your current credit status.</div> :
            <div className="mt-4 space-y-3">
              <div className="flex justify-between text-sm text-slate-600"><span>Subtotal (excl. GST)</span><span className="font-semibold text-slate-900">{formatMoney(cartPreview.subtotal_excl_gst)}</span></div>
              <div className="flex justify-between text-sm text-slate-600"><span>Scheme savings</span><span className="font-semibold text-emerald-700">−{formatMoney(cartPreview.total_discount_excl_gst)}</span></div>
              {cartPreview.all_free_goods && cartPreview.all_free_goods.length > 0 && (
                <div className="rounded-xl border border-emerald-200 bg-emerald-50/90 p-3 text-xs">
                  <div className="flex items-center gap-1.5 font-bold text-emerald-900">
                    <BadgeCheck className="h-4 w-4 text-emerald-700" />
                    Free Benefits Awarded ({cartPreview.all_free_goods.length})
                  </div>
                  <div className="mt-2 space-y-1">
                    {cartPreview.all_free_goods.map((b, idx) => (
                      <div key={idx} className="flex items-center justify-between rounded bg-white px-2 py-1 shadow-xs text-slate-800">
                        <span className="font-medium truncate max-w-[160px]">{b.free_product_name}</span>
                        <span className="font-bold text-emerald-800 text-[10px]">+{b.free_qty} {b.free_uom} FREE</span>
                      </div>
                    ))}
                  </div>
                </div>
              )}
              <div className="border-t border-slate-200 pt-3"><div className="flex justify-between text-sm font-extrabold text-slate-900"><span>Order total</span><span>{formatMoney(cartPreview.subtotal_excl_gst)}</span></div><p className="mt-1 text-[10px] text-slate-500">All amounts exclude GST. Final invoice from distributor.</p></div>
              <div className={`rounded-xl p-3 text-xs leading-5 ${cartPreview.credit_check.will_trigger_credit_hold ? 'bg-amber-50 text-amber-900' : 'bg-emerald-50 text-emerald-900'}`}><div className="font-bold">{cartPreview.credit_check.will_trigger_credit_hold ? 'Credit hold expected' : 'Credit available'}</div><div className="mt-1">{cartPreview.credit_check.notice}</div></div>
              {cartPreview.has_insufficient_stock && <div className="rounded-xl bg-rose-50 p-3 text-xs font-semibold text-rose-800">One or more lines exceed available stock. Update quantities before placing your order.</div>}
              {cartPreview.has_scheme_conflicts && <div className="rounded-xl bg-amber-50 p-3 text-xs text-amber-900">Competing schemes require order desk review. Your order will not silently stack promotions.</div>}
            </div>}
          {cartItems.length > 0 && <>
            <button onClick={reviewCart} disabled={busy} className="tap-button mt-5 flex w-full items-center justify-center gap-2 rounded-xl border border-emerald-200 bg-emerald-50 px-4 py-3 text-sm font-bold text-emerald-800 hover:bg-emerald-100 disabled:opacity-60">{busy ? <LoaderCircle className="h-4 w-4 animate-spin" /> : <Check className="h-4 w-4" />}Review price & schemes</button>
            <button onClick={submitOrder} disabled={busy || !cartPreview || cartPreview.has_insufficient_stock} className="tap-button mt-2 flex w-full items-center justify-center gap-2 rounded-xl bg-[#0d5b40] px-4 py-3 text-sm font-bold text-white hover:bg-[#084a35] disabled:cursor-not-allowed disabled:bg-slate-200 disabled:text-slate-500">{busy ? <LoaderCircle className="h-4 w-4 animate-spin" /> : <ShoppingBag className="h-4 w-4" />}Confirm & place order</button>
            <p className="mt-2 text-center text-[10px] leading-4 text-slate-400">Inventory and credit are checked again by the server at checkout.</p>
          </>}
        </aside>
      </section>
    );
  };

  const renderAI = () => (
    <section className="grid gap-5 xl:grid-cols-[minmax(0,1fr)_320px]">
      <div className="rounded-[22px] border border-slate-200 bg-white p-4 sm:p-6">
        <div className="flex flex-wrap items-start justify-between gap-3">
          <div>
            <p className="flex items-center gap-2 text-xs font-bold uppercase tracking-[.16em] text-emerald-700">
              <Sparkles className="h-4 w-4" /> Multimodal Order Capture
            </p>
            <h2 className="mt-2 text-2xl font-extrabold tracking-[-.04em] text-slate-900">
              AI WhatsApp, Photo & Voice Capture
            </h2>
            <p className="mt-1 text-sm text-slate-500">
              Extract orders from text, handwritten note photos, or Hindi/Hinglish voice recordings. Human review is always mandatory.
            </p>
          </div>
          <span className="rounded-full bg-emerald-50 px-3 py-1.5 text-[11px] font-bold text-emerald-800">
            Human review required
          </span>
        </div>

        {/* Mode selector tabs */}
        <div className="mt-5 flex border-b border-slate-200">
          <button
            onClick={() => { setAiMode('text'); setCapture(null); setReviewedLines([]); }}
            className={`flex items-center gap-2 border-b-2 px-4 py-2.5 text-xs font-bold transition ${aiMode === 'text' ? 'border-[#0d5b40] text-[#0d5b40]' : 'border-transparent text-slate-500 hover:text-slate-800'}`}
          >
            <Sparkles className="h-4 w-4" /> Text Message
          </button>
          <button
            onClick={() => { setAiMode('photo'); setCapture(null); setReviewedLines([]); }}
            className={`flex items-center gap-2 border-b-2 px-4 py-2.5 text-xs font-bold transition ${aiMode === 'photo' ? 'border-[#0d5b40] text-[#0d5b40]' : 'border-transparent text-slate-500 hover:text-slate-800'}`}
          >
            <Camera className="h-4 w-4" /> Handwritten Photo
          </button>
          <button
            onClick={() => { setAiMode('voice'); setCapture(null); setReviewedLines([]); }}
            className={`flex items-center gap-2 border-b-2 px-4 py-2.5 text-xs font-bold transition ${aiMode === 'voice' ? 'border-[#0d5b40] text-[#0d5b40]' : 'border-transparent text-slate-500 hover:text-slate-800'}`}
          >
            <Mic className="h-4 w-4" /> Hindi Voice Audio
          </button>
        </div>

        {/* Text Mode */}
        {aiMode === 'text' && (
          <div className="mt-4">
            <textarea
              value={rawMessage}
              onChange={(event) => { setRawMessage(event.target.value); setCapture(null); setReviewedLines([]); }}
              rows={4}
              maxLength={4000}
              placeholder="Paste an order in Hindi, Hinglish or English… (e.g. 5 peti biscuit, 2 peti detergent)"
              className="w-full resize-y rounded-2xl border border-slate-200 bg-[#fbfcfb] p-4 text-sm leading-6 text-slate-800 outline-none focus:border-emerald-400 focus:ring-4 focus:ring-emerald-50"
            />
            <div className="mt-2 flex flex-wrap items-center justify-between gap-3">
              <p className="text-xs text-slate-400">{rawMessage.length}/4000 characters · Text order parsing</p>
              <button
                disabled={busy}
                onClick={captureMessage}
                className="tap-button inline-flex items-center gap-2 rounded-xl bg-[#0d5b40] px-4 py-3 text-sm font-bold text-white hover:bg-[#084a35] disabled:opacity-60"
              >
                {busy ? <LoaderCircle className="h-4 w-4 animate-spin" /> : <Sparkles className="h-4 w-4" />}
                Extract items from text
              </button>
            </div>
          </div>
        )}

        {/* Photo Mode */}
        {aiMode === 'photo' && (
          <div className="mt-4 rounded-2xl border-2 border-dashed border-slate-200 bg-[#fbfcfb] p-6 text-center">
            <Camera className="mx-auto h-10 w-10 text-emerald-700" />
            <h4 className="mt-2 text-sm font-bold text-slate-800">Upload handwritten order photo</h4>
            <p className="mt-1 text-xs text-slate-500">JPEG, PNG, or WebP up to 10MB. Clear handwriting recommended.</p>
            <input
              ref={photoInputRef}
              type="file"
              accept="image/jpeg,image/png,image/webp"
              onChange={(e) => {
                const file = e.target.files?.[0] || null;
                setPhotoFile(file);
                setCapture(null);
                setReviewedLines([]);
                setError('');
                setUploadErrorModal(null);
              }}
              className="mt-3 block w-full text-xs text-slate-500 file:mr-3 file:rounded-lg file:border-0 file:bg-emerald-50 file:px-3 file:py-2 file:text-xs file:font-bold file:text-emerald-800 hover:file:bg-emerald-100"
            />
            {photoFile && photoPreviewUrl && (
              <div className="mt-3 flex flex-col items-center">
                <img
                  src={photoPreviewUrl}
                  alt="Selected order slip"
                  className="max-h-44 rounded-xl border border-slate-200 object-contain shadow-xs bg-white p-1"
                />
                <p className="mt-1.5 text-xs font-semibold text-emerald-800">
                  {photoFile.name} ({(photoFile.size / 1024).toFixed(1)} KB)
                </p>
              </div>
            )}
            <button
              disabled={busy || !photoFile}
              onClick={capturePhotoOrder}
              className="tap-button mt-4 inline-flex items-center gap-2 rounded-xl bg-[#0d5b40] px-5 py-3 text-sm font-bold text-white hover:bg-[#084a35] disabled:cursor-not-allowed disabled:bg-slate-200 disabled:text-slate-500"
            >
              {busy ? <LoaderCircle className="h-4 w-4 animate-spin" /> : <Camera className="h-4 w-4" />}
              Extract items from photo
            </button>
          </div>
        )}

        {/* Voice Mode */}
        {aiMode === 'voice' && (
          <div className="mt-4 rounded-2xl border-2 border-dashed border-slate-200 bg-[#fbfcfb] p-6 text-center">
            <Mic className="mx-auto h-10 w-10 text-emerald-700" />
            <h4 className="mt-2 text-sm font-bold text-slate-800">Record or upload Hindi voice note</h4>
            <p className="mt-1 text-xs text-slate-500">Audio in Hindi or Hinglish (MP3, WAV, WebM, M4A up to 25MB).</p>

            <div className="mt-4 flex flex-wrap items-center justify-center gap-3">
              {!isRecording ? (
                <button
                  type="button"
                  onClick={() => void startVoiceRecording()}
                  className="tap-button inline-flex items-center gap-2 rounded-xl border border-rose-200 bg-rose-50 px-4 py-2.5 text-xs font-bold text-rose-700 hover:bg-rose-100"
                >
                  <span className="h-2.5 w-2.5 rounded-full bg-rose-600 animate-pulse" />
                  Record live audio
                </button>
              ) : (
                <button
                  type="button"
                  onClick={stopVoiceRecording}
                  className="tap-button inline-flex items-center gap-2 rounded-xl bg-rose-600 px-4 py-2.5 text-xs font-bold text-white hover:bg-rose-700"
                >
                  <MicOff className="h-4 w-4" />
                  Stop recording
                </button>
              )}

              <span className="text-xs text-slate-400">or</span>

              <label className="tap-button inline-flex cursor-pointer items-center gap-2 rounded-xl border border-slate-200 bg-white px-3.5 py-2.5 text-xs font-bold text-slate-700 hover:bg-slate-50">
                <span>Select audio file</span>
                <input
                  type="file"
                  accept="audio/*"
                  onChange={(e) => {
                    const file = e.target.files?.[0] || null;
                    setVoiceFile(file);
                    setCapture(null);
                    setReviewedLines([]);
                    setError('');
                    setUploadErrorModal(null);
                  }}
                  className="hidden"
                />
              </label>
            </div>

            {voiceFile && voiceAudioUrl && (
              <div className="mt-3 flex flex-col items-center rounded-xl bg-emerald-50/60 p-3 border border-emerald-100 max-w-md mx-auto">
                <p className="text-xs font-semibold text-emerald-800">
                  {voiceFile.name} ({(voiceFile.size / 1024).toFixed(1)} KB)
                </p>
                <audio controls src={voiceAudioUrl} className="mt-2 w-full" />
              </div>
            )}

            <button
              disabled={busy || !voiceFile}
              onClick={captureVoiceOrder}
              className="tap-button mt-4 inline-flex items-center gap-2 rounded-xl bg-[#0d5b40] px-5 py-3 text-sm font-bold text-white hover:bg-[#084a35] disabled:cursor-not-allowed disabled:bg-slate-200 disabled:text-slate-500"
            >
              {busy ? <LoaderCircle className="h-4 w-4 animate-spin" /> : <Mic className="h-4 w-4" />}
              Transcribe & extract items
            </button>
          </div>
        )}

        {capture && (
          <div className="mt-6 border-t border-slate-200 pt-5">
            {aiMode === 'photo' && photoPreviewUrl && (
              <div className="mb-5 overflow-hidden rounded-2xl border border-slate-200 bg-white p-3.5 shadow-xs">
                <div className="mb-2 flex items-center justify-between">
                  <span className="flex items-center gap-1.5 text-xs font-bold text-slate-800">
                    <Camera className="h-4 w-4 text-emerald-700" />
                    Uploaded Handwritten Slip
                  </span>
                  <span className="text-[11px] text-slate-500">Cross-check handwriting with detected lines below</span>
                </div>
                <div className="flex max-h-72 justify-center overflow-auto rounded-xl bg-slate-50 p-2 border border-slate-100">
                  <img
                    src={photoPreviewUrl}
                    alt="Uploaded handwritten slip"
                    className="max-h-64 rounded-lg object-contain shadow-sm"
                  />
                </div>
              </div>
            )}

            {aiMode === 'voice' && voiceAudioUrl && (
              <div className="mb-5 rounded-2xl border border-emerald-200 bg-emerald-50/70 p-4 shadow-xs">
                <div className="mb-2 flex items-center justify-between">
                  <span className="flex items-center gap-1.5 text-xs font-bold text-emerald-900">
                    <Mic className="h-4 w-4 text-emerald-700" />
                    Listen to Voice Recording
                  </span>
                  <span className="text-[11px] font-semibold text-emerald-700">Audio playback</span>
                </div>
                <audio controls src={voiceAudioUrl} className="w-full mt-1" />
              </div>
            )}

            <div className="mb-3 flex items-end justify-between gap-3">
              <div>
                <h3 className="text-lg font-extrabold text-slate-900">Suggested order lines</h3>
                <p className="mt-1 text-xs text-slate-500">{capture.model_version} · {capture.lines.length} line(s) extracted</p>
              </div>
              <span className="rounded-full bg-slate-100 px-2.5 py-1 text-[11px] font-bold text-slate-600">
                {reviewedLines.length}/{capture.lines.length} reviewed
              </span>
            </div>
            <div className="space-y-3">
              {capture.lines.map((line) => {
                const resolution = captureResolution[line.id] ?? { productId: '', quantity: line.parsed_quantity, unit: '' as const, saveAlias: false };
                const matched = products.find((product) => product.id === resolution.productId);
                return (
                  <article key={line.id} className="rounded-2xl border border-slate-200 bg-slate-50/80 p-3.5 sm:p-4">
                    <div className="flex items-start justify-between gap-3">
                      <div className="min-w-0">
                        <p className="text-[10px] font-bold uppercase tracking-[.13em] text-slate-400">Original detected text</p>
                        <p className="mt-1 break-words text-sm font-semibold text-slate-800">“{line.raw_line_text}”</p>
                      </div>
                      <span className={`shrink-0 rounded-full px-2 py-1 text-[10px] font-extrabold ${line.confidence_level === 'HIGH' ? 'bg-emerald-100 text-emerald-800' : line.confidence_level === 'MEDIUM' ? 'bg-amber-100 text-amber-800' : 'bg-rose-100 text-rose-800'}`}>
                        {line.confidence_level} · {Math.round(Number(line.confidence_score) * 100)}%
                      </span>
                    </div>
                    <div className="mt-3 grid gap-2 sm:grid-cols-[minmax(0,1fr)_90px_120px]">
                      <label className="text-[10px] font-bold uppercase tracking-[.1em] text-slate-500">Matched SKU
                        <select
                          value={resolution.productId}
                          onChange={(event) => updateResolution(line.id, { productId: event.target.value })}
                          className="mt-1.5 w-full rounded-lg border border-slate-200 bg-white px-3 py-2.5 text-xs font-semibold normal-case tracking-normal text-slate-800 outline-none focus:border-emerald-400"
                        >
                          <option value="">Select a product</option>
                          {products.map((product) => <option key={product.id} value={product.id}>{product.sku_code} · {product.name}</option>)}
                        </select>
                      </label>
                      <label className="text-[10px] font-bold uppercase tracking-[.1em] text-slate-500">Qty
                        <input
                          type="number"
                          min={1}
                          value={resolution.quantity}
                          onChange={(event) => updateResolution(line.id, { quantity: Math.max(1, Number(event.target.value)) })}
                          className="mt-1.5 w-full rounded-lg border border-slate-200 bg-white px-3 py-2.5 text-sm font-bold text-slate-800 outline-none focus:border-emerald-400"
                        />
                      </label>
                      <label className="text-[10px] font-bold uppercase tracking-[.1em] text-slate-500">{line.unit_clarification_needed ? 'Confirm unit' : 'Order unit'}
                        <select
                          value={resolution.unit}
                          onChange={(event) => updateResolution(line.id, { unit: event.target.value as CaptureResolution['unit'] })}
                          className="mt-1.5 w-full rounded-lg border border-slate-200 bg-white px-3 py-2.5 text-xs font-bold normal-case tracking-normal text-slate-800 outline-none focus:border-emerald-400"
                        >
                          <option value="">Choose…</option>
                          <option value="CASE">Cases (peti)</option>
                          <option value="PIECE">Individual pieces</option>
                        </select>
                      </label>
                    </div>
                    {line.unit_clarification_needed && (
                      <p className="mt-2 flex items-start gap-1.5 text-[11px] font-semibold text-amber-800">
                        <CircleHelp className="mt-0.5 h-3.5 w-3.5 shrink-0" />
                        {line.clarification_prompt || 'Confirm whether this means cases or individual pieces. We will not guess.'}
                      </p>
                    )}
                    {line.alternatives.length > 0 && (
                      <p className="mt-2 text-[11px] text-slate-500">
                        Alternatives: {line.alternatives.map((alternative) => `${alternative.sku_code} (${Math.round(Number(alternative.confidence) * 100)}%)`).join(' · ')}
                      </p>
                    )}
                    <div className="mt-3 flex flex-wrap items-center justify-between gap-2 border-t border-slate-200 pt-3">
                      {matched && <span className="text-xs font-semibold text-slate-600">{matched.name} · {formatMoney(matched.effective_price)} excl. GST</span>}
                      <label className="flex items-center gap-2 text-[11px] font-medium text-slate-500">
                        <input
                          type="checkbox"
                          checked={resolution.saveAlias}
                          onChange={(event) => updateResolution(line.id, { saveAlias: event.target.checked })}
                          className="h-4 w-4 rounded border-slate-300 text-emerald-700"
                        />
                        Remember this phrase
                      </label>
                      <button
                        onClick={() => reviewLine(line)}
                        disabled={busy || !resolution.productId || !resolution.unit}
                        className="tap-button inline-flex items-center gap-1.5 rounded-lg border border-emerald-200 bg-white px-3 py-2 text-xs font-bold text-emerald-800 hover:bg-emerald-50 disabled:opacity-50"
                      >
                        {reviewedLines.includes(line.id) ? <Check className="h-3.5 w-3.5" /> : null}
                        {reviewedLines.includes(line.id) ? 'Reviewed' : 'Confirm line'}
                      </button>
                    </div>
                  </article>
                );
              })}
            </div>
            <button
              disabled={busy || !capture.lines.length || reviewedLines.length !== capture.lines.length || capture.lines.some((line) => captureResolution[line.id]?.unit === 'PIECE')}
              onClick={addCaptureToCart}
              className="tap-button mt-4 flex w-full items-center justify-center gap-2 rounded-xl bg-[#0d5b40] px-4 py-3.5 text-sm font-bold text-white hover:bg-[#084a35] disabled:cursor-not-allowed disabled:bg-slate-200 disabled:text-slate-500"
            >
              {busy ? <LoaderCircle className="h-4 w-4 animate-spin" /> : <ShoppingBag className="h-4 w-4" />}
              Confirm reviewed lines & add to cart
            </button>
            {capture.lines.some((line) => captureResolution[line.id]?.unit === 'PIECE') && (
              <p className="mt-2 text-center text-xs font-medium text-amber-800">
                Piece-based checkout is not supported. Change the unit to cases to continue.
              </p>
            )}
          </div>
        )}
      </div>

      <aside className="h-fit rounded-[22px] border border-slate-200 bg-white p-5">
        <div className="flex items-center gap-2">
          <div className="flex h-9 w-9 items-center justify-center rounded-xl bg-emerald-50 text-emerald-700">
            <Headphones className="h-4 w-4" />
          </div>
          <h3 className="font-extrabold text-slate-900">How Multimodal AI Works</h3>
        </div>
        <ol className="mt-4 space-y-4">
          {[
            ['Text / Photo / Voice', 'Paste WhatsApp text, upload a handwritten slip photo, or speak in Hindi.'],
            ['Catalog Matching', 'AI extracts quantities and finds the closest matching catalogue SKUs and confidence scores.'],
            ['Human Review', 'You must verify every item and unit. Uncertain lines and pieces vs cases must be confirmed.'],
            ['Checkout Validation', 'Live stock, active schemes, and retailer credit are checked securely upon checkout.'],
          ].map(([title, detail], index) => (
            <li key={title} className="flex gap-3">
              <span className="flex h-6 w-6 shrink-0 items-center justify-center rounded-full bg-emerald-50 text-[11px] font-extrabold text-emerald-800">
                {index + 1}
              </span>
              <div>
                <div className="text-xs font-bold text-slate-800">{title}</div>
                <p className="mt-1 text-[11px] leading-4 text-slate-500">{detail}</p>
              </div>
            </li>
          ))}
        </ol>
        <div className="mt-5 rounded-xl bg-amber-50 p-3 text-[11px] leading-5 text-amber-900">
          <b>Safe by design:</b> AI never places orders autonomously. Retailer credit and inventory are strictly server-validated.
        </div>
      </aside>
    </section>
  );

  const renderOrders = () => {
    const statusTone = (status: string) => status.includes('APPROVED') ? 'green' : status.includes('HOLD') ? 'amber' : status.includes('REJECT') ? 'rose' : 'blue';
    return (
      <section className="space-y-4">
        {offlineQueue.length > 0 && (
          <div className="rounded-[22px] border border-amber-200 bg-amber-50/70 p-4 sm:p-5">
            <div className="flex items-center justify-between gap-3">
              <div>
                <p className="text-[10px] font-bold uppercase tracking-wider text-amber-800">Local Queue</p>
                <h3 className="text-base font-extrabold text-amber-950">Pending Offline Orders ({offlineQueue.length})</h3>
                <p className="text-xs text-amber-800/80">These orders were created offline and will sync automatically when connectivity returns.</p>
              </div>
              <button
                disabled={busy || !isOnline}
                onClick={() => void syncOfflineOrders()}
                className="tap-button inline-flex items-center gap-1.5 rounded-xl bg-amber-800 px-3.5 py-2 text-xs font-bold text-white hover:bg-amber-900 disabled:opacity-50"
              >
                {busy ? <LoaderCircle className="h-3.5 w-3.5 animate-spin" /> : <RefreshCw className="h-3.5 w-3.5" />}
                Sync Orders
              </button>
            </div>
            <div className="mt-3 space-y-2">
              {offlineQueue.map((offOrder) => (
                <div key={offOrder.clientOrderId} className="flex flex-wrap items-center justify-between gap-2 rounded-xl bg-white p-3 text-xs shadow-xs">
                  <div>
                    <span className="font-mono text-slate-500 font-semibold">ID: {offOrder.clientOrderId.slice(0, 8)}...</span>
                    <span className="ml-2 font-bold text-slate-800">{offOrder.items.length} item(s)</span>
                    <span className="ml-2 text-slate-400">{new Date(offOrder.createdAt).toLocaleTimeString()}</span>
                  </div>
                  <div className="flex items-center gap-2">
                    <span className={`rounded-full px-2 py-0.5 text-[10px] font-extrabold ${offOrder.status === 'SYNC_FAILED' ? 'bg-rose-100 text-rose-800' : 'bg-amber-100 text-amber-800'}`}>
                      {offOrder.status.replace(/_/g, ' ')}
                    </span>
                    {offOrder.error && <span className="text-[10px] text-rose-600">{offOrder.error}</span>}
                  </div>
                </div>
              ))}
            </div>
          </div>
        )}

        <div className="rounded-[22px] border border-slate-200 bg-white p-4 sm:p-6">
          <div className="mb-5 flex flex-wrap items-end justify-between gap-3">
            <div>
              <p className="text-xs font-bold uppercase tracking-[.16em] text-emerald-700">Order history</p>
              <h2 className="mt-1 text-2xl font-extrabold tracking-[-.04em] text-slate-900">My orders</h2>
            </div>
            <button onClick={() => showScreen('catalogue')} className="tap-button rounded-xl bg-[#0d5b40] px-4 py-2.5 text-sm font-bold text-white hover:bg-[#084a35]">
              New order
            </button>
          </div>

          {dataLoading && !orders.length ? (
            <LoadingState label="Loading your orders…" />
          ) : orders.length ? (
            <div className="space-y-2">
              {orders.map((order) => (
                <div key={order.id} className="overflow-hidden rounded-xl border border-slate-200">
                  <div className="flex w-full flex-wrap items-center justify-between gap-3 p-3.5 hover:bg-slate-50 sm:p-4">
                    <button
                      onClick={() => void fetchRetailerOrderDetails(order)}
                      className="flex-1 text-left min-w-[200px]"
                    >
                      <div className="text-sm font-extrabold text-slate-900">{order.order_number}</div>
                      <div className="mt-1 text-xs text-slate-500">
                        {new Date(order.created_at).toLocaleString('en-IN')} · {order.item_count} item(s)
                      </div>
                    </button>
                    <div className="flex flex-wrap items-center gap-3">
                      <StatusPill status={order.status} tone={statusTone(order.status)} />
                      <span className="text-sm font-extrabold text-slate-900">{formatMoney(order.subtotal_excl_gst)}</span>
                      <button
                        onClick={() => void openRepeatOrder(order)}
                        className="tap-button inline-flex items-center gap-1.5 rounded-lg border border-emerald-300 bg-emerald-50 px-2.5 py-1.5 text-xs font-bold text-emerald-800 hover:bg-emerald-100"
                      >
                        <RotateCcw className="h-3.5 w-3.5" /> Repeat Order
                      </button>
                      <button
                        onClick={() => void fetchRetailerOrderDetails(order)}
                        className="rounded-lg p-1 text-slate-400 hover:text-slate-600"
                        aria-label="Expand order lines"
                      >
                        <ChevronDown className={`h-4 w-4 transition ${selectedOrder?.id === order.id ? 'rotate-180' : ''}`} />
                      </button>
                    </div>
                  </div>

                  {selectedOrder?.id === order.id && selectedOrder.items && (
                    <div className="border-t border-slate-100 bg-slate-50/60 px-4 py-3">
                      <div className="space-y-2">
                        {selectedOrder.items.map((line) => (
                          <div key={line.id} className="rounded-lg bg-white p-2.5 text-xs border border-slate-100">
                            <div className="flex items-center justify-between gap-3">
                              <span className="font-bold text-slate-800">
                                {line.product_name_snapshot} <span className="text-slate-400">· {line.sku_code_snapshot}</span>
                              </span>
                              <span className="font-semibold text-slate-700">
                                {line.approved_qty} case(s) · {formatMoney(line.line_subtotal_excl_gst)}
                              </span>
                            </div>
                            {line.benefits && line.benefits.length > 0 ? (
                              <div className="mt-1.5 space-y-1 pl-2 border-l-2 border-emerald-500">
                                {line.benefits.map((b) => (
                                  <div key={b.id} className="flex items-center justify-between text-[11px] text-emerald-800">
                                    <span>Free Benefit: {b.free_product_name} ({b.free_sku_code})</span>
                                    <span className="font-extrabold bg-emerald-100 px-1.5 py-0.5 rounded text-[10px]">
                                      +{b.free_qty} {b.free_uom} FREE
                                    </span>
                                  </div>
                                ))}
                              </div>
                            ) : line.free_item_qty > 0 ? (
                              <div className="mt-1 text-[11px] font-semibold text-emerald-700">
                                Free Good: {line.free_product_name_snapshot || 'Promotion item'} ({line.free_sku_code_snapshot || 'FREE'}) +{line.free_item_qty} case(s)
                              </div>
                            ) : null}
                          </div>
                        ))}
                      </div>
                      {selectedOrder.credit_hold_reason && (
                        <p className="mt-3 rounded-lg bg-amber-50 p-2 text-xs text-amber-900">{selectedOrder.credit_hold_reason}</p>
                      )}
                    </div>
                  )}
                </div>
              ))}
            </div>
          ) : (
            <EmptyState
              title="No orders yet"
              message="Your submitted orders will appear here with their live status."
              action="Browse catalogue"
              onAction={() => showScreen('catalogue')}
            />
          )}
        </div>
      </section>
    );
  };

  const renderDesk = () => {
    const filtered = orderFilter === 'All' ? deskOrders : deskOrders.filter((order) => order.status === orderFilter);
    return <section className="rounded-[22px] border border-slate-200 bg-white p-4 sm:p-6">
      <div className="mb-5 flex flex-wrap items-end justify-between gap-3">
        <div>
          <p className="text-xs font-bold uppercase tracking-[.16em] text-emerald-700">Distributor workspace</p>
          <h2 className="mt-1 text-2xl font-extrabold tracking-[-.04em] text-slate-900">Order desk</h2>
          <p className="mt-1 text-sm text-slate-500">Review retailer orders, resolve credit holds, and approve for picking.</p>
        </div>
        <div className="flex items-center gap-2">
          <button onClick={() => showScreen('van')} className="tap-button inline-flex items-center gap-2 rounded-xl border border-slate-200 bg-white px-3 py-2.5 text-sm font-bold text-slate-700 hover:bg-slate-50">
            <Truck className="h-4 w-4" /> Van list
          </button>
          <button onClick={() => showScreen('exports')} className="tap-button inline-flex items-center gap-2 rounded-xl border border-slate-200 bg-white px-3 py-2.5 text-sm font-bold text-slate-700 hover:bg-slate-50">
            <FileSpreadsheet className="h-4 w-4" /> Tally exports
          </button>
        </div>
      </div>
      <div className="mb-4 flex flex-wrap gap-2">{['All', 'PENDING_DESK_APPROVAL', 'CREDIT_HOLD', 'APPROVED'].map((filter) => <button key={filter} onClick={() => setOrderFilter(filter)} className={`rounded-full px-3 py-2 text-xs font-bold ${orderFilter === filter ? 'bg-[#0d5b40] text-white' : 'bg-slate-100 text-slate-600 hover:bg-slate-200'}`}>{filter === 'PENDING_DESK_APPROVAL' ? 'Needs review' : filter.replace(/_/g, ' ').toLowerCase().replace(/^./, (character: string) => character.toUpperCase())}</button>)}</div>
      {dataLoading && !deskOrders.length ? <LoadingState label="Loading order desk queue…" /> : filtered.length ? <div className="overflow-x-auto rounded-xl border border-slate-200"><table className="w-full min-w-[690px] text-left"><thead className="bg-slate-50 text-[10px] font-bold uppercase tracking-[.1em] text-slate-500"><tr><th className="px-4 py-3">Order</th><th className="px-4 py-3">Retailer</th><th className="px-4 py-3">Amount</th><th className="px-4 py-3">Status</th><th className="px-4 py-3 text-right">Actions</th></tr></thead><tbody className="divide-y divide-slate-100">
        {filtered.map((order) => <tr key={order.id} className="text-sm hover:bg-slate-50/70"><td className="px-4 py-3"><button onClick={() => void openDeskOrder(order)} className="font-extrabold text-emerald-800 hover:underline">{order.order_number}</button><div className="mt-0.5 text-[10px] text-slate-400">{order.item_count} line(s)</div></td><td className="px-4 py-3 font-semibold text-slate-700">{order.retailer_name || order.retailer_code || 'Retailer'}</td><td className="px-4 py-3 font-semibold text-slate-800">{formatMoney(order.subtotal_excl_gst)}</td><td className="px-4 py-3"><StatusPill status={order.status} tone={order.status === 'CREDIT_HOLD' ? 'amber' : order.status === 'APPROVED' ? 'green' : order.status === 'REJECTED' ? 'rose' : 'blue'} /></td><td className="px-4 py-3 text-right"><div className="inline-flex gap-1.5">{order.status === 'PENDING_DESK_APPROVAL' || order.status === 'CREDIT_HOLD' ? <><button disabled={busy} onClick={() => void approveDeskOrder(order)} className="rounded-lg bg-[#0d5b40] px-3 py-2 text-[11px] font-bold text-white disabled:opacity-50">{order.status === 'CREDIT_HOLD' ? 'Override & approve' : 'Approve'}</button><button disabled={busy} onClick={() => void holdDeskOrder(order)} className="rounded-lg border border-slate-200 bg-white px-3 py-2 text-[11px] font-bold text-slate-600 disabled:opacity-50">Hold</button></> : <button onClick={() => void openDeskOrder(order)} className="rounded-lg border border-slate-200 px-3 py-2 text-[11px] font-bold text-slate-700">Details</button>}</div></td></tr>)}
      </tbody></table></div> : <EmptyState title="No orders in this queue" message="New retailer orders will appear here as soon as they are submitted." action="Refresh queue" onAction={() => void loadDeskData()} />}
      {selectedDeskOrder && <div className="mt-5 rounded-2xl border border-emerald-100 bg-emerald-50/50 p-4"><div className="flex items-start justify-between gap-3"><div><p className="text-[10px] font-bold uppercase tracking-[.12em] text-emerald-700">Selected order</p><h3 className="mt-1 text-base font-extrabold text-slate-900">{selectedDeskOrder.order_number} · {selectedDeskOrder.retailer_name || 'Retailer'}</h3></div><button aria-label="Close order detail" onClick={() => setSelectedDeskOrder(null)} className="rounded-lg p-1.5 text-slate-500 hover:bg-white"><X className="h-4 w-4" /></button></div>
        {selectedDeskOrder.items?.length ? <div className="mt-3 space-y-2">{selectedDeskOrder.items.map((line) => (
          <div key={line.id} className="rounded-lg bg-white p-3 text-xs border border-emerald-100/50">
            <div className="flex flex-wrap justify-between gap-2">
              <span className="font-bold text-slate-800">{line.product_name_snapshot} · {line.sku_code_snapshot}</span>
              <span className="text-slate-600">{line.ordered_qty} ordered / {line.approved_qty} approved · {formatMoney(line.line_subtotal_excl_gst)}</span>
            </div>
            {line.benefits && line.benefits.length > 0 ? (
              <div className="mt-2 space-y-1 pl-2 border-l-2 border-emerald-500">
                {line.benefits.map((b) => (
                  <div key={b.id} className="flex items-center justify-between text-[11px] text-emerald-800">
                    <span>Awarded Free Benefit: {b.free_product_name} ({b.free_sku_code})</span>
                    <span className="font-extrabold bg-emerald-100 px-1.5 py-0.5 rounded text-[10px]">+{b.free_qty} {b.free_uom} FREE</span>
                  </div>
                ))}
              </div>
            ) : line.free_item_qty > 0 ? (
              <div className="mt-1 text-[11px] text-emerald-700">
                Free Good: {line.free_product_name_snapshot || 'Promotion item'} ({line.free_sku_code_snapshot || 'FREE'}) +{line.free_item_qty} case(s)
              </div>
            ) : null}
          </div>
        ))}</div> : <p className="mt-3 text-xs text-slate-500">Loading order lines…</p>}
        {selectedDeskOrder.credit_hold_reason && <p className="mt-3 text-xs text-amber-900">{selectedDeskOrder.credit_hold_reason}</p>}</div>}
    </section>;
  };

  const renderVanLoadingList = () => {
    const items = vanData?.items ?? [];
    const totalPurchased = items.reduce((sum, item) => sum + Number(item.purchased_quantity), 0);
    const totalFree = items.reduce((sum, item) => sum + Number(item.free_quantity), 0);

    const downloadVanCsv = async () => {
      setBusy(true);
      setError('');
      try {
        const blob = await api.downloadVanLoadingCsv(vanFromDate || undefined, vanToDate || undefined);
        const url = URL.createObjectURL(blob);
        const a = document.createElement('a');
        a.href = url;
        a.download = `van_loading_list_${new Date().toISOString().split('T')[0]}.csv`;
        a.click();
        URL.revokeObjectURL(url);
      } catch (err) {
        setError(errorMessage(err));
      } finally {
        setBusy(false);
      }
    };

    return (
      <section className="space-y-5">
        <div className="rounded-[22px] border border-slate-200 bg-white p-4 sm:p-6">
          <div className="flex flex-wrap items-start justify-between gap-3">
            <div>
              <p className="text-xs font-bold uppercase tracking-[.16em] text-emerald-700">Warehouse & Dispatch</p>
              <h2 className="mt-1 text-2xl font-extrabold tracking-[-.04em] text-slate-900">Van Loading List</h2>
              <p className="mt-1 text-sm text-slate-500">
                Aggregated pick-and-load list for approved orders. Purchased stock and scheme free goods are strictly separated to prevent warehouse confusion.
              </p>
            </div>
            <div className="flex flex-wrap items-center gap-2">
              <button
                onClick={() => window.print()}
                className="tap-button inline-flex items-center gap-1.5 rounded-xl border border-slate-200 bg-white px-3.5 py-2.5 text-xs font-bold text-slate-700 hover:bg-slate-50"
              >
                <Printer className="h-4 w-4" /> Print Sheet
              </button>
              <button
                disabled={busy || !items.length}
                onClick={() => void downloadVanCsv()}
                className="tap-button inline-flex items-center gap-1.5 rounded-xl bg-[#0d5b40] px-4 py-2.5 text-xs font-bold text-white hover:bg-[#084a35] disabled:cursor-not-allowed disabled:bg-slate-200 disabled:text-slate-500"
              >
                <Download className="h-4 w-4" /> Export CSV
              </button>
            </div>
          </div>

          <div className="mt-5 flex flex-wrap items-center gap-3 rounded-xl bg-slate-50 p-3">
            <span className="text-xs font-bold text-slate-700">Filter dispatch batch:</span>
            <label className="flex items-center gap-1.5 text-xs text-slate-600">
              From:
              <input
                type="date"
                value={vanFromDate}
                onChange={(e) => setVanFromDate(e.target.value)}
                className="rounded-lg border border-slate-200 bg-white px-2 py-1.5 text-xs outline-none"
              />
            </label>
            <label className="flex items-center gap-1.5 text-xs text-slate-600">
              To:
              <input
                type="date"
                value={vanToDate}
                onChange={(e) => setVanToDate(e.target.value)}
                className="rounded-lg border border-slate-200 bg-white px-2 py-1.5 text-xs outline-none"
              />
            </label>
            <button
              onClick={() => void loadVanData()}
              className="tap-button rounded-lg bg-[#0d5b40] px-3 py-1.5 text-xs font-bold text-white hover:bg-[#084a35]"
            >
              Filter
            </button>
            {(vanFromDate || vanToDate) && (
              <button
                onClick={() => { setVanFromDate(''); setVanToDate(''); void api.vanLoadingList().then(setVanData); }}
                className="text-xs font-semibold text-emerald-700 underline"
              >
                Reset
              </button>
            )}
          </div>

          <div className="mt-5 grid gap-3 sm:grid-cols-4">
            <div className="rounded-xl bg-slate-50 p-3">
              <p className="text-[10px] font-bold uppercase tracking-wider text-slate-500">Approved Orders</p>
              <p className="mt-1 text-xl font-extrabold text-slate-900">{vanData?.approved_orders_count ?? 0}</p>
            </div>
            <div className="rounded-xl bg-slate-50 p-3">
              <p className="text-[10px] font-bold uppercase tracking-wider text-slate-500">Unique SKUs</p>
              <p className="mt-1 text-xl font-extrabold text-slate-900">{items.length}</p>
            </div>
            <div className="rounded-xl bg-emerald-50 p-3">
              <p className="text-[10px] font-bold uppercase tracking-wider text-emerald-800">Purchased Cases</p>
              <p className="mt-1 text-xl font-extrabold text-emerald-900">{totalPurchased}</p>
            </div>
            <div className="rounded-xl bg-emerald-50 p-3">
              <p className="text-[10px] font-bold uppercase tracking-wider text-emerald-800">Free Benefit Goods</p>
              <p className="mt-1 text-xl font-extrabold text-emerald-900">{totalFree} free cases</p>
            </div>
          </div>

          {dataLoading && !vanData ? (
            <LoadingState label="Calculating van loading manifest from approved orders…" />
          ) : items.length ? (
            <div className="mt-5 overflow-x-auto rounded-xl border border-slate-200">
              <table className="w-full min-w-[700px] text-left">
                <thead className="bg-slate-50 text-[10px] font-bold uppercase tracking-[.1em] text-slate-500">
                  <tr>
                    <th className="px-4 py-3">SKU & Product</th>
                    <th className="px-4 py-3">Category</th>
                    <th className="px-4 py-3 text-right">Purchased</th>
                    <th className="px-4 py-3 text-right text-emerald-700">Free Goods</th>
                    <th className="px-4 py-3 text-right">Total Load</th>
                    <th className="px-4 py-3 text-right">Stores</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-slate-100 text-sm">
                  {items.map((item) => {
                    const isExpanded = expandedVanSku === item.sku_code;
                    return (
                      <tr key={item.sku_code} className="hover:bg-slate-50/70">
                        <td className="px-4 py-3">
                          <span className="font-extrabold text-slate-900">{item.product_name}</span>
                          <div className="text-[10px] font-mono text-slate-400">{item.sku_code}</div>
                        </td>
                        <td className="px-4 py-3 text-xs text-slate-600">{item.category}</td>
                        <td className="px-4 py-3 text-right font-semibold text-slate-800">
                          {item.purchased_quantity} cases
                        </td>
                        <td className="px-4 py-3 text-right font-extrabold text-emerald-700">
                          {item.free_quantity > 0 ? `+${item.free_quantity} free` : '—'}
                        </td>
                        <td className="px-4 py-3 text-right font-extrabold text-slate-900">
                          {item.total_cases} cases
                        </td>
                        <td className="px-4 py-3 text-right">
                          <button
                            onClick={() => setExpandedVanSku(isExpanded ? null : item.sku_code)}
                            className="inline-flex items-center gap-1 text-xs font-bold text-emerald-700 hover:underline"
                          >
                            {item.store_breakdowns.length} stores
                            <ChevronDown className={`h-3.5 w-3.5 transition ${isExpanded ? 'rotate-180' : ''}`} />
                          </button>
                        </td>
                      </tr>
                    );
                  })}
                </tbody>
              </table>
            </div>
          ) : (
            <EmptyState
              title="No approved orders to load"
              message="Approve pending orders in the Order Desk to generate the van loading list."
              action="Go to Order Desk"
              onAction={() => showScreen('desk')}
            />
          )}
        </div>
      </section>
    );
  };

  const renderInactivity = () => {
    const items = inactivityData?.items ?? [];

    const downloadInactivityCsv = async () => {
      setBusy(true);
      setError('');
      try {
        const blob = await api.downloadInactiveRetailersCsv(inactivityDays);
        const url = URL.createObjectURL(blob);
        const a = document.createElement('a');
        a.href = url;
        a.download = `inactive_retailers_${inactivityDays}days.csv`;
        a.click();
        URL.revokeObjectURL(url);
      } catch (err) {
        setError(errorMessage(err));
      } finally {
        setBusy(false);
      }
    };

    return (
      <section className="space-y-5">
        <div className="rounded-[22px] border border-slate-200 bg-white p-4 sm:p-6">
          <div className="flex flex-wrap items-start justify-between gap-3">
            <div>
              <p className="text-xs font-bold uppercase tracking-[.16em] text-emerald-700">Account Health & Churn Detection</p>
              <h2 className="mt-1 text-2xl font-extrabold tracking-[-.04em] text-slate-900">Retailer Inactivity Report</h2>
              <p className="mt-1 text-sm text-slate-500">
                Kirana stores with no confirmed orders in the last {inactivityDays} days. Follow up with field sales to re-engage accounts.
              </p>
            </div>
            <button
              disabled={busy || !items.length}
              onClick={() => void downloadInactivityCsv()}
              className="tap-button inline-flex items-center gap-1.5 rounded-xl bg-[#0d5b40] px-4 py-2.5 text-xs font-bold text-white hover:bg-[#084a35] disabled:cursor-not-allowed disabled:bg-slate-200 disabled:text-slate-500"
            >
              <Download className="h-4 w-4" /> Download Inactivity CSV
            </button>
          </div>

          <div className="mt-5 flex flex-wrap items-center justify-between gap-3 rounded-xl bg-slate-50 p-3">
            <div className="flex flex-wrap items-center gap-3">
              <span className="text-xs font-bold text-slate-700">Inactivity threshold:</span>
              {[7, 14, 30, 60].map((d) => (
                <button
                  key={d}
                  onClick={() => { setInactivityDays(d); void api.inactiveRetailers(d, inactivitySearch || undefined, 1).then(setInactivityData); }}
                  className={`rounded-lg px-3 py-1.5 text-xs font-bold ${inactivityDays === d ? 'bg-[#0d5b40] text-white' : 'bg-white text-slate-700 border border-slate-200'}`}
                >
                  {d} days
                </button>
              ))}
            </div>

            <div className="relative w-full sm:w-64">
              <Search className="absolute left-3 top-1/2 h-3.5 w-3.5 -translate-y-1/2 text-slate-400" />
              <input
                value={inactivitySearch}
                onChange={(e) => {
                  setInactivitySearch(e.target.value);
                  void api.inactiveRetailers(inactivityDays, e.target.value || undefined, 1).then(setInactivityData);
                }}
                placeholder="Search store name or code…"
                className="w-full rounded-lg border border-slate-200 bg-white py-1.5 pl-8 pr-3 text-xs outline-none focus:border-emerald-400"
              />
            </div>
          </div>

          <div className="mt-5 grid gap-3 sm:grid-cols-3">
            <div className="rounded-xl bg-rose-50 p-3">
              <p className="text-[10px] font-bold uppercase tracking-wider text-rose-800">Inactive Retailers (&gt;{inactivityDays}d)</p>
              <p className="mt-1 text-2xl font-extrabold text-rose-900">{inactivityData?.inactive_retailers_count ?? 0}</p>
            </div>
            <div className="rounded-xl bg-slate-50 p-3">
              <p className="text-[10px] font-bold uppercase tracking-wider text-slate-500">Total Registered Stores</p>
              <p className="mt-1 text-2xl font-extrabold text-slate-900">{inactivityData?.total_retailers_count ?? 0}</p>
            </div>
            <div className="rounded-xl bg-amber-50 p-3">
              <p className="text-[10px] font-bold uppercase tracking-wider text-amber-800">Inactivity Percentage</p>
              <p className="mt-1 text-2xl font-extrabold text-amber-900">
                {inactivityData?.total_retailers_count
                  ? Math.round((inactivityData.inactive_retailers_count / inactivityData.total_retailers_count) * 100)
                  : 0}%
              </p>
            </div>
          </div>

          {dataLoading && !inactivityData ? (
            <LoadingState label="Auditing retailer order history and churn timestamps…" />
          ) : items.length ? (
            <>
              <div className="mt-5 overflow-x-auto rounded-xl border border-slate-200">
                <table className="w-full min-w-[700px] text-left">
                  <thead className="bg-slate-50 text-[10px] font-bold uppercase tracking-[.1em] text-slate-500">
                    <tr>
                      <th className="px-4 py-3">Retailer</th>
                      <th className="px-4 py-3">Phone</th>
                      <th className="px-4 py-3 text-right">Credit / Exposure</th>
                      <th className="px-4 py-3">Last Order</th>
                      <th className="px-4 py-3 text-right">Days Inactive</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-slate-100 text-sm">
                    {items.map((ret) => (
                      <tr key={ret.retailer_id} className="hover:bg-slate-50/70">
                        <td className="px-4 py-3">
                          <span className="font-extrabold text-slate-900">{ret.store_name}</span>
                          <div className="text-[10px] font-mono text-slate-400">{ret.retailer_code}</div>
                        </td>
                        <td className="px-4 py-3 text-xs text-slate-600 font-mono">
                          {ret.phone_number ? `+91 ${ret.phone_number}` : '—'}
                        </td>
                        <td className="px-4 py-3 text-right text-xs">
                          <div className="font-semibold text-slate-800">{formatMoney(ret.current_exposure)}</div>
                          <div className="text-[10px] text-slate-400">Limit: {formatMoney(ret.credit_limit)}</div>
                        </td>
                        <td className="px-4 py-3 text-xs text-slate-600">
                          {ret.last_confirmed_order_date
                            ? new Date(ret.last_confirmed_order_date).toLocaleDateString('en-IN')
                            : <span className="font-semibold text-amber-700">Never ordered</span>}
                        </td>
                        <td className="px-4 py-3 text-right">
                          <span className={`inline-block rounded-full px-2.5 py-1 text-[11px] font-extrabold ${ret.days_since_last_order === null ? 'bg-amber-100 text-amber-800' : 'bg-rose-100 text-rose-800'}`}>
                            {ret.days_since_last_order !== null ? `${ret.days_since_last_order} days` : 'No history'}
                          </span>
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>

              {inactivityData && inactivityData.total_pages > 1 && (
                <div className="mt-4 flex items-center justify-between text-xs text-slate-600">
                  <span>Page {inactivityData.page} of {inactivityData.total_pages}</span>
                  <div className="flex gap-2">
                    <button
                      disabled={inactivityData.page <= 1}
                      onClick={() => void loadInactivityData(inactivityData.page - 1)}
                      className="rounded-lg border border-slate-200 px-3 py-1.5 font-bold disabled:opacity-40"
                    >
                      Previous
                    </button>
                    <button
                      disabled={inactivityData.page >= inactivityData.total_pages}
                      onClick={() => void loadInactivityData(inactivityData.page + 1)}
                      className="rounded-lg border border-slate-200 px-3 py-1.5 font-bold disabled:opacity-40"
                    >
                      Next
                    </button>
                  </div>
                </div>
              )}
            </>
          ) : (
            <EmptyState
              title="No inactive retailers found"
              message={`Every kirana store has placed a confirmed order within the last ${inactivityDays} days.`}
            />
          )}
        </div>
      </section>
    );
  };

  const renderRepeatOrderModal = () => {
    if (!repeatPreview) return null;
    return (
      <div className="fixed inset-0 z-50 flex items-center justify-center bg-slate-950/60 p-4 backdrop-blur-xs">
        <div className="max-h-[90vh] w-full max-w-2xl overflow-y-auto rounded-[24px] border border-slate-200 bg-white p-6 shadow-2xl">
          <div className="flex items-start justify-between gap-3">
            <div>
              <span className="inline-flex items-center gap-1 text-[11px] font-bold uppercase tracking-wider text-emerald-700">
                <RotateCcw className="h-3.5 w-3.5" /> Revalidated Repeat Order
              </span>
              <h3 className="mt-1 text-xl font-extrabold text-slate-900">
                Repeat Order Review
              </h3>
              <p className="mt-0.5 text-xs text-slate-500">
                Live catalog revalidation of prices, current inventory availability, active schemes, and retailer credit.
              </p>
            </div>
            <button
              onClick={() => { setRepeatPreview(null); setRepeatSourceOrder(null); }}
              className="rounded-lg p-1.5 text-slate-400 hover:bg-slate-100 hover:text-slate-700"
            >
              <X className="h-5 w-5" />
            </button>
          </div>

          {!repeatPreview.can_repeat && repeatPreview.blocker_reason && (
            <div className="mt-4 rounded-xl border border-rose-200 bg-rose-50 p-3 text-xs font-semibold text-rose-800">
              <AlertCircle className="inline mr-1.5 h-4 w-4 text-rose-600 align-text-bottom" />
              {repeatPreview.blocker_reason}
            </div>
          )}

          <div className="mt-4 overflow-hidden rounded-xl border border-slate-200">
            <table className="w-full text-left text-xs">
              <thead className="bg-slate-50 text-[10px] font-bold uppercase tracking-wider text-slate-500">
                <tr>
                  <th className="px-3 py-2.5">Product</th>
                  <th className="px-3 py-2.5 text-center">Qty</th>
                  <th className="px-3 py-2.5 text-right">Price Diff</th>
                  <th className="px-3 py-2.5 text-right">Subtotal</th>
                  <th className="px-3 py-2.5 text-right">Status</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-100">
                {repeatPreview.lines.map((l) => (
                  <tr key={l.product_id} className={l.is_out_of_stock ? 'bg-rose-50/50' : ''}>
                    <td className="px-3 py-2.5">
                      <div className="font-bold text-slate-900">{l.product_name}</div>
                      <div className="text-[10px] text-slate-400">{l.sku_code}</div>
                    </td>
                    <td className="px-3 py-2.5 text-center font-semibold">
                      {l.new_qty} cases
                    </td>
                    <td className="px-3 py-2.5 text-right">
                      <div>{formatMoney(l.current_price)}</div>
                      {l.price_changed && (
                        <div className="text-[10px] text-amber-700">was {formatMoney(l.old_price)}</div>
                      )}
                    </td>
                    <td className="px-3 py-2.5 text-right font-bold text-slate-900">
                      {formatMoney(l.current_subtotal)}
                    </td>
                    <td className="px-3 py-2.5 text-right">
                      {l.is_out_of_stock ? (
                        <span className="rounded bg-rose-100 px-1.5 py-0.5 text-[10px] font-bold text-rose-800">Out of Stock</span>
                      ) : l.schemes_changed ? (
                        <span className="rounded bg-emerald-100 px-1.5 py-0.5 text-[10px] font-bold text-emerald-800">Schemes active</span>
                      ) : (
                        <span className="rounded bg-slate-100 px-1.5 py-0.5 text-[10px] font-bold text-slate-600">Available</span>
                      )}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>

          <div className="mt-4 grid gap-3 sm:grid-cols-2 rounded-xl bg-slate-50 p-3 text-xs">
            <div>
              <div className="text-slate-500">Original order amount: <span className="font-semibold text-slate-800">{formatMoney(repeatPreview.original_subtotal_excl_gst)}</span></div>
              <div className="text-slate-500 mt-1">Revalidated total: <span className="font-extrabold text-slate-900">{formatMoney(repeatPreview.revalidated_subtotal_excl_gst)}</span></div>
            </div>
            <div>
              <div className="text-slate-500">Available credit: <span className="font-semibold text-slate-800">{formatMoney(repeatPreview.available_credit)}</span></div>
              <div className={`mt-1 font-bold ${repeatPreview.is_credit_blocked ? 'text-amber-800' : 'text-emerald-700'}`}>
                {repeatPreview.is_credit_blocked ? 'Will trigger credit hold' : 'Credit check passed'}
              </div>
            </div>
          </div>

          <div className="mt-5 flex items-center justify-end gap-3">
            <button
              onClick={() => { setRepeatPreview(null); setRepeatSourceOrder(null); }}
              className="rounded-xl border border-slate-200 px-4 py-2.5 text-xs font-bold text-slate-700 hover:bg-slate-50"
            >
              Cancel
            </button>
            <button
              disabled={!repeatPreview.can_repeat}
              onClick={confirmRepeatToCart}
              className="tap-button inline-flex items-center gap-2 rounded-xl bg-[#0d5b40] px-5 py-2.5 text-xs font-bold text-white hover:bg-[#084a35] disabled:cursor-not-allowed disabled:bg-slate-200 disabled:text-slate-500"
            >
              <ShoppingBag className="h-4 w-4" /> Load Validated Items to Cart
            </button>
          </div>
        </div>
      </div>
    );
  };

  const approvedOrders = deskOrders.filter((order) => order.status === 'APPROVED');
  const renderExports = () => <section className="space-y-5">
    <div className="rounded-[22px] border border-slate-200 bg-white p-4 sm:p-6">
      <div className="flex flex-wrap items-start justify-between gap-3"><div><p className="text-xs font-bold uppercase tracking-[.16em] text-emerald-700">Accounting handoff</p><h2 className="mt-1 text-2xl font-extrabold tracking-[-.04em] text-slate-900">Tally export</h2><p className="mt-1 max-w-xl text-sm leading-6 text-slate-500">Generate a Tally-compatible CSV from approved orders. Exported orders are marked as exported in the order desk.</p></div><span className="rounded-full bg-emerald-50 px-3 py-1.5 text-xs font-bold text-emerald-800">{approvedOrders.length} approved</span></div>
      {approvedOrders.length ? <div className="mt-5 space-y-2">{approvedOrders.map((order) => <label key={order.id} className="flex cursor-pointer items-center justify-between gap-3 rounded-xl border border-slate-200 p-3 hover:bg-slate-50"><span className="flex items-center gap-3"><input type="checkbox" checked={selectedExportOrders.includes(order.id)} onChange={(event) => setSelectedExportOrders((current) => event.target.checked ? [...current, order.id] : current.filter((id) => id !== order.id))} className="h-4 w-4 rounded border-slate-300 text-emerald-700" /><span><b className="block text-sm text-slate-800">{order.order_number}</b><span className="text-xs text-slate-500">{order.retailer_name || order.retailer_code} · {order.item_count} lines</span></span></span><b className="text-sm text-slate-900">{formatMoney(order.subtotal_excl_gst)}</b></label>)}</div> : <div className="mt-5 rounded-xl bg-slate-50 p-4 text-sm text-slate-600">No approved orders are available. Approve an order in the order desk before exporting.</div>}
      <button onClick={generateExport} disabled={busy || !approvedOrders.length} className="tap-button mt-4 inline-flex items-center gap-2 rounded-xl bg-[#0d5b40] px-4 py-3 text-sm font-bold text-white hover:bg-[#084a35] disabled:cursor-not-allowed disabled:bg-slate-200 disabled:text-slate-500">{busy ? <LoaderCircle className="h-4 w-4 animate-spin" /> : <FileSpreadsheet className="h-4 w-4" />}Generate Tally CSV {selectedExportOrders.length ? `(${selectedExportOrders.length})` : '(all approved)'}</button>
    </div>
    <div className="rounded-[22px] border border-slate-200 bg-white p-4 sm:p-6"><h3 className="text-lg font-extrabold text-slate-900">Export history</h3>{exportBatches.length ? <div className="mt-4 divide-y divide-slate-100">{exportBatches.map((batch) => <div key={batch.id} className="flex flex-wrap items-center justify-between gap-3 py-3"><span><b className="block text-sm text-slate-800">{batch.batch_number}</b><span className="text-xs text-slate-500">{batch.file_name} · {batch.order_count} order(s) · {formatMoney(batch.total_amount_excl_gst)}</span></span><button onClick={() => void downloadBatch(batch)} disabled={busy} className="tap-button inline-flex items-center gap-2 rounded-lg border border-slate-200 px-3 py-2 text-xs font-bold text-slate-700 hover:bg-slate-50"><ArrowDownToLine className="h-4 w-4" />Download</button></div>)}</div> : <p className="mt-3 text-sm text-slate-500">No export batches generated yet.</p>}</div>
  </section>;

  const renderAccount = () => (
    <section className="max-w-2xl rounded-[22px] border border-slate-200 bg-white p-5 sm:p-7 shadow-xs">
      <div className="flex items-center gap-4">
        <div className="flex h-14 w-14 items-center justify-center rounded-2xl bg-emerald-50 text-emerald-800 font-extrabold text-lg">
          {user.full_name.split(' ').map((part) => part[0]).slice(0, 2).join('')}
        </div>
        <div>
          <h2 className="text-xl font-extrabold text-slate-900">{user.full_name}</h2>
          <p className="mt-1 text-sm text-slate-500">
            {role === 'retailer' ? retailerName : 'Order Desk Supervisor'} · +91 {user.phone_number}
          </p>
        </div>
      </div>
      {retailer ? (
        <div className="mt-6 grid gap-3 sm:grid-cols-2">
          <InfoField label="Store" value={retailer.store_name} />
          <InfoField label="Retailer code" value={retailer.retailer_code} />
          <InfoField label="Credit limit" value={formatMoney(retailer.credit_limit)} />
          <InfoField label="Outstanding" value={formatMoney(retailer.outstanding_amount)} />
          <InfoField label="Available credit" value={formatMoney(retailer.available_credit)} />
          <InfoField label="Pricing tier" value={retailer.pricing_tier.replace(/_/g, ' ')} />
        </div>
      ) : (
        <div className="mt-6 grid gap-3 sm:grid-cols-2">
          <InfoField label="Role" value="Order Desk Supervisor / Ops Lead" />
          <InfoField label="Station" value="Jabalpur FMCG Distribution HQ" />
          <InfoField label="Queue access" value="Approval, Credit Hold Override, Van Dispatch" />
          <InfoField label="Accounting" value="Tally ERP XML/CSV Exporter Enabled" />
        </div>
      )}
      <button onClick={() => void signOut()} className="tap-button mt-6 inline-flex items-center gap-2 rounded-xl border border-rose-200 bg-rose-50 px-4 py-3 text-sm font-bold text-rose-800 hover:bg-rose-100">
        <LogOut className="h-4 w-4" />Sign out
      </button>
    </section>
  );

  return (
    <div className="app-shell min-h-screen bg-[#f6f8f6] text-slate-800">
      <aside className="app-sidebar flex w-[232px] shrink-0 flex-col px-4 py-5 text-white">
        <button onClick={() => showScreen(role === 'retailer' ? 'catalogue' : 'desk')} className="mb-7 flex items-center gap-3 px-2 text-left">
          <span className="flex h-10 w-10 items-center justify-center rounded-xl bg-white text-sm font-black text-[#0b553b] shadow-sm">VS</span><span><b className="block text-[17px] font-extrabold leading-5">VyapaarSetu</b><span className="text-[10px] font-medium tracking-wide text-emerald-100">Grow Together</span></span>
        </button>
        <div className="mb-3 px-2 text-[10px] font-bold uppercase tracking-[.16em] text-emerald-100/65">{role === 'retailer' ? 'Retailer workspace' : 'Distributor workspace'}</div>
        <nav className="space-y-1.5">{visibleNav.map((item) => {
          const Icon = item.icon;
          const active = screen === item.id || (screen === 'exports' && item.id === 'exports');
          return <button key={item.id} onClick={() => showScreen(item.id)} className={`nav-item flex w-full items-center gap-3 rounded-xl px-3 py-3 text-left text-[13px] font-semibold transition ${active ? 'bg-emerald-600/80 text-white shadow-sm' : 'text-emerald-50/85 hover:bg-white/10 hover:text-white'}`}><Icon className="h-[17px] w-[17px]" />{item.label}{item.id === 'cart' && cartCount > 0 ? <span className="ml-auto rounded-full bg-white px-2 py-0.5 text-[10px] font-extrabold text-emerald-800">{cartCount}</span> : null}</button>;
        })}</nav>
        {role === 'retailer' && <div className="sidebar-promo mt-auto rounded-2xl border border-white/10 bg-white/[.06] p-3.5"><div className="flex h-8 w-8 items-center justify-center rounded-lg bg-emerald-300/15 text-emerald-200"><Home className="h-4 w-4" /></div><p className="mt-3 text-xs font-bold leading-5">Smart ordering for a growing business</p><p className="mt-1 text-[10px] leading-4 text-emerald-100/70">Your prices and credit are private to your account.</p></div>}
        <div className="sidebar-user mt-4 flex items-center gap-2.5 border-t border-white/10 pt-4"><div className="flex h-9 w-9 items-center justify-center rounded-full bg-white/15 text-xs font-extrabold">{user.full_name.split(' ').map((part) => part[0]).slice(0, 2).join('')}</div><div className="min-w-0 flex-1"><p className="truncate text-xs font-bold">{retailerName}</p><p className="truncate text-[10px] text-emerald-100/70">{role === 'retailer' ? retailer?.city || 'Jabalpur' : 'Order desk'}</p></div><button onClick={() => showScreen('account')} aria-label="Account options" className="rounded-lg p-1.5 hover:bg-white/10"><ChevronDown className="h-4 w-4" /></button></div>
      </aside>
      <main className="min-w-0 flex-1">
        <header className="app-header sticky top-0 z-30 flex items-center gap-3 border-b border-slate-200/70 bg-white/90 px-4 py-3.5 backdrop-blur-xl sm:px-6">
          <div className="relative min-w-0 flex-1">
            <Search className="absolute left-3.5 top-1/2 h-4 w-4 -translate-y-1/2 text-slate-400" />
            <input value={query} onChange={(event) => setQuery(event.target.value)} placeholder={role === 'retailer' ? 'Search products… (e.g. biscuit, detergent)' : 'Filter by order, retailer, or SKU…'} className="w-full max-w-[680px] rounded-full border border-slate-200 bg-[#fafbfa] py-2.5 pl-10 pr-4 text-sm outline-none placeholder:text-slate-400 focus:border-emerald-300" />
          </div>
          <div className="hidden items-center gap-2 rounded-full border border-slate-200 bg-white px-2 py-1.5 sm:flex"><div className="flex h-8 w-8 items-center justify-center rounded-full bg-[#0f5a40] text-[10px] font-extrabold text-white">{user.full_name.split(' ').map((part) => part[0]).slice(0, 2).join('')}</div><div className="max-w-[170px]"><p className="truncate text-xs font-bold text-slate-800">{retailerName}</p><p className="text-[10px] text-slate-500">{role === 'retailer' ? retailer?.city || 'Jabalpur, MP' : 'Order desk'}</p></div><button onClick={() => showScreen('account')} aria-label="Open account" className="p-1 text-slate-500"><ChevronDown className="h-4 w-4" /></button></div>
          {role === 'retailer' ? (
            <button onClick={() => showScreen('cart')} aria-label="Shopping cart" className="tap-button relative flex h-10 w-10 items-center justify-center rounded-full border border-slate-200 bg-white text-slate-600 hover:text-emerald-800"><ShoppingBag className="h-4 w-4" />{cartCount > 0 && <span className="absolute -right-1 -top-1 flex h-[18px] min-w-[18px] items-center justify-center rounded-full bg-rose-500 px-1 text-[9px] font-bold text-white">{cartCount}</span>}</button>
          ) : (
            <button onClick={() => showScreen('desk')} aria-label="Order Desk Queue" className="tap-button inline-flex items-center gap-1.5 rounded-full border border-emerald-200 bg-emerald-50 px-3 py-1.5 text-xs font-bold text-emerald-800 hover:bg-emerald-100"><BriefcaseBusiness className="h-3.5 w-3.5 text-emerald-700" /><span>Queue ({deskOrders.filter((o) => o.status === 'PENDING_DESK_APPROVAL' || o.status === 'CREDIT_HOLD').length})</span></button>
          )}
        </header>
        <div className="page-content mx-auto max-w-[1500px] px-3 pb-24 pt-4 sm:px-5 sm:pt-5 lg:px-7">
          <div className="mb-4 flex items-center justify-between gap-3"><div><p className="text-[11px] font-semibold text-slate-500">{role === 'retailer' ? 'Retailer portal' : 'Distributor portal'} <span className="px-1 text-slate-300">/</span> Jabalpur</p><h1 className="mt-0.5 text-xl font-extrabold tracking-[-.035em] text-slate-900">{titleMap[screen]}</h1></div>{dataLoading && <span className="inline-flex items-center gap-1.5 text-xs font-semibold text-slate-500"><LoaderCircle className="h-3.5 w-3.5 animate-spin" />Updating</span>}</div>
          {error && (
            <div className="mb-4">
              <ErrorBanner
                message={error}
                onDismiss={() => {
                  setError('');
                  setUploadErrorModal(null);
                }}
                onRetry={() => {
                  if (aiMode === 'photo') {
                    retryPhotoUpload();
                  } else if (aiMode === 'voice') {
                    retryVoiceUpload();
                  } else {
                    setError('');
                  }
                }}
              />
            </div>
          )}
          {!isOnline && (
            <div className="mb-4 flex items-center justify-between rounded-xl border border-amber-300 bg-amber-50 px-4 py-3 text-xs font-semibold text-amber-900 shadow-xs">
              <span className="flex items-center gap-2">
                <WifiOff className="h-4 w-4 text-amber-700 shrink-0" />
                Offline Salesman Mode Active: You can browse cached products and submit orders locally.
              </span>
            </div>
          )}
          {offlineQueue.length > 0 && (
            <div className="mb-4 flex items-center justify-between rounded-xl border border-emerald-300 bg-emerald-50 px-4 py-3 text-xs font-semibold text-emerald-900 shadow-xs">
              <span className="flex items-center gap-2">
                <Package className="h-4 w-4 text-emerald-700 shrink-0" />
                {offlineQueue.length} offline order(s) queued for sync.
              </span>
              <button
                disabled={busy || !isOnline}
                onClick={() => void syncOfflineOrders()}
                className="tap-button inline-flex items-center gap-1.5 rounded-lg bg-[#0d5b40] px-3 py-1.5 text-xs font-bold text-white hover:bg-[#084a35] disabled:cursor-not-allowed disabled:bg-slate-300 disabled:text-slate-500"
              >
                {busy ? <LoaderCircle className="h-3.5 w-3.5 animate-spin" /> : <RefreshCw className="h-3.5 w-3.5" />}
                Sync Now
              </button>
            </div>
          )}
          {notice && <div className="mb-4 flex items-start justify-between gap-3 rounded-xl border border-emerald-200 bg-emerald-50 px-3.5 py-3 text-sm text-emerald-900"><span className="flex items-start gap-2"><Check className="mt-0.5 h-4 w-4 shrink-0" />{notice}</span><button onClick={() => setNotice('')} aria-label="Dismiss message"><X className="h-4 w-4" /></button></div>}
          {screen === 'catalogue' && renderCatalogue()}
          {screen === 'cart' && renderCart()}
          {screen === 'ai' && renderAI()}
          {screen === 'orders' && renderOrders()}
          {screen === 'desk' && renderDesk()}
          {screen === 'van' && renderVanLoadingList()}
          {screen === 'inactivity' && renderInactivity()}
          {screen === 'exports' && renderExports()}
          {screen === 'account' && renderAccount()}
          {renderRepeatOrderModal()}
          {uploadErrorModal && (
            <AppAlertModal
              error={uploadErrorModal}
              onDismiss={() => setUploadErrorModal(null)}
              onRetry={() => {
                if (uploadErrorModal.mode === 'photo') {
                  retryPhotoUpload();
                } else {
                  retryVoiceUpload();
                }
              }}
            />
          )}
        </div>
      </main>
      <nav className="mobile-nav fixed inset-x-0 bottom-0 z-40 grid border-t border-slate-200 bg-white/95 px-1 pb-[env(safe-area-inset-bottom)] pt-1.5 backdrop-blur-lg md:hidden" style={{ gridTemplateColumns: `repeat(${Math.min(visibleNav.length, 5)}, minmax(0, 1fr))` }}>
        {visibleNav.slice(0, 5).map((item) => {
          const Icon = item.icon;
          return <button key={item.id} onClick={() => showScreen(item.id)} className={`flex min-h-[54px] flex-col items-center justify-center gap-1 rounded-lg text-[9px] font-bold ${screen === item.id ? 'text-emerald-800' : 'text-slate-500'}`}><span className="relative"><Icon className="h-[18px] w-[18px]" />{item.id === 'cart' && cartCount > 0 ? <span className="absolute -right-2 -top-1 flex h-3.5 min-w-3.5 items-center justify-center rounded-full bg-rose-500 px-1 text-[8px] text-white">{cartCount}</span> : null}</span>{item.label}</button>;
        })}
      </nav>
    </div>
  );
}

function MetricCard({ icon: Icon, title, amount, sub, tone, action }: { icon: typeof CreditCard; title: string; amount: string; sub: string; tone: string; action?: () => void }) {
  return <button onClick={action} disabled={!action} className={`metric-card flex min-h-[96px] items-center gap-3.5 rounded-[18px] border border-slate-200/80 bg-white px-4 py-4 text-left shadow-[0_2px_8px_rgba(15,23,42,.025)] ${action ? 'cursor-pointer hover:border-emerald-200' : 'cursor-default'}`}>
    <span className={`flex h-11 w-11 shrink-0 items-center justify-center rounded-2xl ${tone === 'green' ? 'bg-emerald-50 text-emerald-700' : tone === 'blue' ? 'bg-sky-50 text-sky-700' : tone === 'purple' ? 'bg-violet-50 text-violet-700' : 'bg-amber-50 text-amber-700'}`}><Icon className="h-5 w-5" /></span>
    <span className="min-w-0"><span className="block text-[11px] font-semibold text-slate-500">{title}</span><span className="mt-0.5 block truncate text-[20px] font-extrabold leading-6 tracking-[-.035em] text-slate-900">{amount}</span><span className="mt-1 block truncate text-[10px] text-slate-500">{sub}</span></span>
  </button>;
}

function StatusPill({ status, tone }: { status: string; tone: string }) {
  const color = tone === 'green' ? 'bg-emerald-50 text-emerald-800' : tone === 'amber' ? 'bg-amber-50 text-amber-800' : tone === 'rose' ? 'bg-rose-50 text-rose-800' : 'bg-sky-50 text-sky-800';
  return <span className={`inline-flex items-center rounded-full px-2.5 py-1 text-[10px] font-bold ${color}`}>{status.replace(/_/g, ' ')}</span>;
}

function InfoField({ label, value }: { label: string; value: string }) {
  return <div className="rounded-xl bg-slate-50 p-3"><p className="text-[10px] font-bold uppercase tracking-[.1em] text-slate-500">{label}</p><p className="mt-1 text-sm font-bold text-slate-800">{value}</p></div>;
}

function ErrorBanner({
  message,
  onDismiss,
  onRetry,
}: {
  message: string;
  onDismiss?: () => void;
  onRetry?: () => void;
}) {
  const isIncorrectUpload =
    message.toLowerCase().includes('incorrect') ||
    message.toLowerCase().includes('not a valid grocery order') ||
    message.toLowerCase().includes('no grocery order');

  return (
    <div
      role="alert"
      className="relative overflow-hidden rounded-2xl border border-rose-200 bg-white p-4 shadow-sm shadow-rose-200/40"
    >
      <div className="flex items-start gap-3.5">
        <div className="flex h-10 w-10 shrink-0 items-center justify-center rounded-2xl bg-gradient-to-br from-rose-500 to-rose-600 text-white shadow-md shadow-rose-500/25">
          <AlertCircle className="h-5 w-5" />
        </div>
        <div className="flex-1 pr-4">
          <div className="flex items-center gap-2">
            <span className="rounded-md bg-rose-100 px-2 py-0.5 text-[10px] font-extrabold uppercase tracking-wider text-rose-800">
              {isIncorrectUpload ? 'Upload Alert' : 'Attention'}
            </span>
            <h4 className="text-sm font-bold text-slate-900">
              {isIncorrectUpload ? 'Incorrect Order Upload' : 'Notice'}
            </h4>
          </div>
          <p className="mt-1 text-xs leading-relaxed text-slate-600">{message}</p>
          {onRetry && (
            <button
              onClick={onRetry}
              className="tap-button mt-2.5 inline-flex items-center gap-1.5 rounded-lg bg-rose-50 px-3 py-1.5 text-xs font-bold text-rose-700 hover:bg-rose-100"
            >
              <RotateCcw className="h-3.5 w-3.5" />
              Try again with correct slip
            </button>
          )}
        </div>
        {onDismiss && (
          <button
            onClick={onDismiss}
            aria-label="Dismiss error"
            className="rounded-full p-1.5 text-slate-400 hover:bg-slate-100 hover:text-slate-600 transition"
          >
            <X className="h-4 w-4" />
          </button>
        )}
      </div>
    </div>
  );
}

function AppAlertModal({
  error,
  onDismiss,
  onRetry,
}: {
  error: { mode: 'photo' | 'voice' | 'general'; title: string; message: string };
  onDismiss: () => void;
  onRetry: () => void;
}) {
  const isPhoto = error.mode === 'photo';
  const isVoice = error.mode === 'voice';

  return (
    <div
      role="dialog"
      aria-modal="true"
      className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-slate-900/65 backdrop-blur-sm animate-in fade-in duration-200"
      onClick={(e) => {
        if (e.target === e.currentTarget) onDismiss();
      }}
    >
      <div className="relative w-full max-w-md overflow-hidden rounded-3xl bg-white p-6 shadow-2xl ring-1 ring-slate-900/10 transition-all animate-in zoom-in-95 duration-200">
        <button
          onClick={onDismiss}
          className="absolute right-4 top-4 rounded-full p-2 text-slate-400 hover:bg-slate-100 hover:text-slate-600 transition"
          aria-label="Close alert"
        >
          <X className="h-5 w-5" />
        </button>

        <div className="flex flex-col items-center text-center">
          <div className="relative mb-3 flex h-20 w-20 items-center justify-center rounded-3xl bg-gradient-to-br from-rose-500 via-rose-600 to-amber-500 text-white shadow-xl shadow-rose-500/30 ring-8 ring-rose-50">
            {isPhoto ? (
              <Camera className="h-10 w-10 text-white" />
            ) : isVoice ? (
              <Mic className="h-10 w-10 text-white" />
            ) : (
              <AlertTriangle className="h-10 w-10 text-white" />
            )}
            <span className="absolute -bottom-1 -right-1 flex h-7 w-7 items-center justify-center rounded-full bg-rose-600 text-white ring-4 ring-white">
              <X className="h-4 w-4 stroke-[3]" />
            </span>
          </div>

          <span className="inline-flex items-center gap-1.5 rounded-full bg-rose-100 px-3 py-1 text-[11px] font-extrabold uppercase tracking-wider text-rose-800">
            Upload Alert
          </span>

          <h3 className="mt-2 text-xl font-black tracking-tight text-slate-900">
            {error.title}
          </h3>

          <p className="mt-2 text-xs leading-relaxed text-slate-600 max-w-sm">
            {error.message}
          </p>
        </div>

        <div className="mt-5 rounded-2xl bg-amber-50/70 border border-amber-200/80 p-4 text-left">
          <p className="flex items-center gap-2 text-xs font-bold text-amber-900">
            <Sparkles className="h-4 w-4 text-amber-600" />
            Tips for Kirana Order Detection:
          </p>
          <ul className="mt-2 space-y-1.5 text-[11px] text-amber-950/85">
            {isPhoto ? (
              <>
                <li className="flex items-start gap-2">
                  <span className="font-bold text-emerald-700">✓</span>
                  <span><strong>Handwritten Grocery Slip:</strong> Include item name & quantity (e.g. <em>5 peti biscuit, 2 kg surf</em>).</span>
                </li>
                <li className="flex items-start gap-2">
                  <span className="font-bold text-emerald-700">✓</span>
                  <span><strong>Lighting & Angle:</strong> Capture straight from above with good light, avoiding shadows.</span>
                </li>
                <li className="flex items-start gap-2">
                  <span className="font-bold text-rose-600">✕</span>
                  <span><strong>Avoid:</strong> Selfies, scenery, vehicles, blank paper, or blurry scribbles.</span>
                </li>
              </>
            ) : isVoice ? (
              <>
                <li className="flex items-start gap-2">
                  <span className="font-bold text-emerald-700">✓</span>
                  <span><strong>Speak Items & Units:</strong> Clearly say <em>"5 peti Parle-G chhota, 2 peti detergent powder"</em>.</span>
                </li>
                <li className="flex items-start gap-2">
                  <span className="font-bold text-emerald-700">✓</span>
                  <span><strong>Language:</strong> Hindi, Hinglish, or English are all recognized.</span>
                </li>
                <li className="flex items-start gap-2">
                  <span className="font-bold text-rose-600">✕</span>
                  <span><strong>Avoid:</strong> Loud background noise/music or greetings without item names.</span>
                </li>
              </>
            ) : (
              <>
                <li className="flex items-start gap-2">
                  <span className="font-bold text-emerald-700">✓</span>
                  <span>Provide clear FMCG product names and quantities.</span>
                </li>
              </>
            )}
          </ul>
        </div>

        <div className="mt-6 flex flex-col sm:flex-row gap-2.5">
          <button
            type="button"
            onClick={onRetry}
            className="tap-button flex-1 inline-flex items-center justify-center gap-2 rounded-2xl bg-gradient-to-r from-[#0d5b40] to-[#137a56] px-5 py-3.5 text-sm font-bold text-white shadow-lg shadow-emerald-900/20 hover:from-[#094732] hover:to-[#0d5b40] transition"
          >
            {isPhoto ? <Camera className="h-4 w-4" /> : isVoice ? <Mic className="h-4 w-4" /> : <RotateCcw className="h-4 w-4" />}
            {isPhoto ? 'Upload Correct Photo' : isVoice ? 'Record Voice Again' : 'Try Again'}
          </button>
          <button
            type="button"
            onClick={onDismiss}
            className="tap-button inline-flex items-center justify-center rounded-2xl border border-slate-200 bg-slate-100 px-5 py-3.5 text-sm font-bold text-slate-700 hover:bg-slate-200 transition"
          >
            Dismiss
          </button>
        </div>
      </div>
    </div>
  );
}

function LoadingState({ label }: { label: string }) {
  return <div className="flex items-center justify-center gap-2 rounded-2xl border border-slate-200 bg-white px-4 py-12 text-sm font-medium text-slate-500"><LoaderCircle className="h-4 w-4 animate-spin text-emerald-700" />{label}</div>;
}

function EmptyState({ title, message = 'Try a different selection or come back shortly.', action, onAction }: { title: string; message?: string; action?: string; onAction?: () => void }) {
  return <div className="rounded-2xl border border-dashed border-slate-300 bg-white px-5 py-12 text-center"><div className="mx-auto flex h-11 w-11 items-center justify-center rounded-2xl bg-slate-100 text-slate-500"><Package className="h-5 w-5" /></div><h3 className="mt-3 text-sm font-extrabold text-slate-800">{title}</h3><p className="mx-auto mt-1 max-w-sm text-xs leading-5 text-slate-500">{message}</p>{action && onAction && <button onClick={onAction} className="tap-button mt-4 rounded-lg bg-[#0d5b40] px-3.5 py-2 text-xs font-bold text-white">{action}</button>}</div>;
}

export default App;
