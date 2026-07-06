import {
  Archive,
  BookOpen,
  Cloud,
  Heart,
  Home,
  HelpCircle,
  MessageCircle,
  Mic,
  Network,
  PersonStanding,
  PhoneCall,
  Settings,
  Sprout,
  UserRound,
  Zap,
  type LucideIcon,
} from 'lucide-react';

// all illustration paths, one place to swap an image
export const ILLUSTRATIONS = {
  appIcon: '/illustrations/axis-app-icon.png',
  homeHero: '/illustrations/warm-dashboard-2.jpg',
  homeInsight: '/illustrations/home-insight.png',
  homeMood: '/illustrations/home-mood.png',
  homeHeart: '/illustrations/home-heart.png',
  memoryBook: '/illustrations/memory-book.png',
  memoryLeaf: '/illustrations/memory-leaf.png',
  memoryEmpty: '/illustrations/memory-empty.png',
  memoryArtExperience: '/illustrations/memory-art-1.png',
  memoryArtSubject: '/illustrations/memory-art-2.png',
  memoryArtEmotion: '/illustrations/memory-art-3.png',
  phqHeader: '/illustrations/phq-header.png',
} as const;

// icon per top-level concept, shared by bottom nav, header, and dashboard
export const CONCEPT_ICONS: Record<string, LucideIcon> = {
  beranda: Home,
  chat: MessageCircle,
  confession: Mic,
  memori: BookOpen,
  knowledgeGraph: Network,
  hotline: PhoneCall,
  bantuan: HelpCircle,
  pengaturan: Settings,
  profil: UserRound,
};

/**
 * Icon per memory node type (used by MemoryMapHub's Peta Memori spokes),
 * keyed the same way as MemoryCard.tsx's illustration-per-type map above
 * -- both represent the same 7 node types, just as an icon vs. an image.
 * NOTE: "memory" (Archive) and "topic" (BookOpen) vs. CONCEPT_ICONS.memori
 * (also BookOpen) is a known naming mismatch -- both "memory" the node
 * type and "memori" the nav concept are labeled "Memori" in the UI (see
 * MemoryCard.tsx's TYPE_LABELS) but don't share an icon. Left as-is for
 * now per instruction to gather first, decide later.
 */
export const MEMORY_TYPE_ICONS: Record<string, LucideIcon> = {
  experience: Sprout,
  thought: Cloud,
  memory: Archive,
  emotion: Heart,
  topic: BookOpen,
  behaviour: PersonStanding,
  trigger: Zap,
};

/**
 * Every icon used anywhere in frontend_v2, re-exported from one place --
 * pure pass-through (same names, same components, no choices changed)
 * so every page/component can import icons from '@/lib/assets' instead
 * of 'lucide-react' directly. This is step one (gather); which icon
 * represents which concept is a separate decision for later.
 */
export {
  AlertCircle,
  AlertTriangle,
  Archive,
  ArrowLeft,
  BookOpen,
  Briefcase,
  Check,
  CheckCheck,
  CheckCircle2,
  ChevronDown,
  ChevronLeft,
  ChevronRight,
  ChevronUp,
  ClipboardList,
  Cloud,
  Copy,
  Download,
  Edit3,
  ExternalLink,
  Eye,
  EyeOff,
  Flower2,
  Frown,
  Globe,
  GraduationCap,
  Hand,
  Heart,
  HeartHandshake,
  HelpCircle,
  Home,
  Info,
  Laugh,
  Leaf,
  List,
  Loader2,
  Lock,
  LogOut,
  Mail,
  MapPinned,
  Meh,
  MessageCircle,
  MessageCirclePlus,
  Mic,
  Minus,
  MoreHorizontal,
  MoreVertical,
  MoveDiagonal,
  Network,
  Pencil,
  PersonStanding,
  Phone,
  PhoneCall,
  Play,
  Plus,
  RefreshCw,
  RotateCcw,
  Search,
  Send,
  Settings,
  Shield,
  ShieldAlert,
  ShieldCheck,
  Smartphone,
  Smile,
  Sparkles,
  Sprout,
  Square,
  Star,
  Trash2,
  User,
  UserCog,
  UserRound,
  UsersRound,
  Volume2,
  X,
  Zap,
  ZoomIn,
} from 'lucide-react';
