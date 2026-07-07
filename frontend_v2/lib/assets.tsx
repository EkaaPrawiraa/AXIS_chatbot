import React from "react";
import { FontAwesomeIcon } from "@fortawesome/react-fontawesome";
import {
  faCircleExclamation,
  faTriangleExclamation,
  faBoxArchive,
  faArrowLeft,
  faBookOpen,
  faBriefcase,
  faCheck,
  faCheckDouble,
  faCircleCheck,
  faChevronDown,
  faChevronLeft,
  faChevronRight,
  faChevronUp,
  faClipboardList,
  faCloud,
  faCopy,
  faDownload,
  faPenToSquare,
  faArrowUpRightFromSquare,
  faEye,
  faEyeSlash,
  faSeedling,
  faFaceFrown,
  faGlobe,
  faGraduationCap,
  faHand,
  faHeart,
  faHandshakeAngle,
  faCircleQuestion,
  faHouse,
  faCircleInfo,
  faFaceLaugh,
  faLeaf,
  faList,
  faCircleNotch,
  faLock,
  faRightFromBracket,
  faEnvelope,
  faMapPin,
  faFaceMeh,
  faComment,
  faCommentMedical,
  faMicrophone,
  faMinus,
  faEllipsis,
  faEllipsisVertical,
  faArrowsUpDownLeftRight,
  faNetworkWired,
  faPen,
  faPerson,
  faPhone,
  faPhoneVolume,
  faPlay,
  faPlus,
  faArrowsRotate,
  faRotateLeft,
  faMagnifyingGlass,
  faPaperPlane,
  faGear,
  faShield,
  faShieldHalved,
  faUserShield,
  faMobileScreenButton,
  faFaceSmile,
  faWandMagicSparkles,
  faSquare,
  faStar,
  faTrashCan,
  faUser,
  faUserGear,
  faUsers,
  faVolumeHigh,
  faXmark,
  faBolt,
  faMagnifyingGlassPlus,
  faLanguage,
  faMicrophoneLines,
  faComments,
  faEnvelopeCircleCheck,
  faSliders
} from "@fortawesome/free-solid-svg-icons";

// Wrapper utility to make FontAwesome icons act like Lucide icons
// This allows us to use them directly as components like <Home className="..." />
const createIcon = (icon: any, defaultClasses: string = "") => {
  return ({ className, ...props }: any) => (
    <FontAwesomeIcon icon={icon} className={`${defaultClasses} ${className || ""}`.trim()} {...props} />
  );
};

export const AlertCircle = createIcon(faCircleExclamation);
export const AlertTriangle = createIcon(faTriangleExclamation);
export const Archive = createIcon(faBoxArchive);
export const ArrowLeft = createIcon(faArrowLeft);
export const BookOpen = createIcon(faBookOpen);
export const Briefcase = createIcon(faBriefcase);
export const Check = createIcon(faCheck);
export const CheckCheck = createIcon(faCheckDouble);
export const CheckCircle2 = createIcon(faCircleCheck);
export const ChevronDown = createIcon(faChevronDown);
export const ChevronLeft = createIcon(faChevronLeft);
export const ChevronRight = createIcon(faChevronRight);
export const ChevronUp = createIcon(faChevronUp);
export const ClipboardList = createIcon(faClipboardList);
export const Cloud = createIcon(faCloud);
export const Copy = createIcon(faCopy);
export const Download = createIcon(faDownload);
export const Edit3 = createIcon(faPenToSquare);
export const ExternalLink = createIcon(faArrowUpRightFromSquare);
export const Eye = createIcon(faEye);
export const EyeOff = createIcon(faEyeSlash);
export const Flower2 = createIcon(faSeedling);
export const Frown = createIcon(faFaceFrown);
export const Globe = createIcon(faGlobe);
export const GraduationCap = createIcon(faGraduationCap);
export const Hand = createIcon(faHand);
export const Heart = createIcon(faHeart);
export const HeartHandshake = createIcon(faHandshakeAngle);
export const HelpCircle = createIcon(faCircleQuestion);
export const Home = createIcon(faHouse);
export const Info = createIcon(faCircleInfo);
export const Laugh = createIcon(faFaceLaugh);
export const Leaf = createIcon(faLeaf);
export const List = createIcon(faList);
export const Loader2 = createIcon(faCircleNotch, "fa-spin");
export const Lock = createIcon(faLock);
export const LogOut = createIcon(faRightFromBracket);
export const Mail = createIcon(faEnvelope);
export const MapPinned = createIcon(faMapPin);
export const Meh = createIcon(faFaceMeh);
export const MessageCircle = createIcon(faComment);
export const MessageCirclePlus = createIcon(faCommentMedical);
export const Mic = createIcon(faMicrophone);
export const Minus = createIcon(faMinus);
export const MoreHorizontal = createIcon(faEllipsis);
export const MoreVertical = createIcon(faEllipsisVertical);
export const MoveDiagonal = createIcon(faArrowsUpDownLeftRight);
export const Network = createIcon(faNetworkWired);
export const Pencil = createIcon(faPen);
export const PersonStanding = createIcon(faPerson);
export const Phone = createIcon(faPhone);
export const PhoneCall = createIcon(faPhoneVolume);
export const Play = createIcon(faPlay);
export const Plus = createIcon(faPlus);
export const RefreshCw = createIcon(faArrowsRotate);
export const RotateCcw = createIcon(faRotateLeft);
export const Search = createIcon(faMagnifyingGlass);
export const Send = createIcon(faPaperPlane);
export const Settings = createIcon(faGear);
export const Shield = createIcon(faShield);
export const ShieldAlert = createIcon(faShieldHalved);
export const ShieldCheck = createIcon(faUserShield);
export const Smartphone = createIcon(faMobileScreenButton);
export const Smile = createIcon(faFaceSmile);
export const Sparkles = createIcon(faWandMagicSparkles);
export const Sprout = createIcon(faSeedling);
export const Square = createIcon(faSquare);
export const Star = createIcon(faStar);
export const Trash2 = createIcon(faTrashCan);
export const User = createIcon(faUser);
export const UserCog = createIcon(faUserGear);
export const UserRound = createIcon(faUser);
export const UsersRound = createIcon(faUsers);
export const Volume2 = createIcon(faVolumeHigh);
export const X = createIcon(faXmark);
export const Zap = createIcon(faBolt);
export const ZoomIn = createIcon(faMagnifyingGlassPlus);

// all illustration paths, one place to swap an image
export const ILLUSTRATIONS = {
  appIcon: "/illustrations/axis-app-icon.png",
  homeHero: "/illustrations/warm-dashboard-3.jpg",
  homeInsight: "/illustrations/home-insight.png",
  homeMood: "/illustrations/home-mood-2.png",
  homeHeart: "/illustrations/home-heart-4.png",
  memoryBook: "/illustrations/memory-book.png",
  memoryLeaf: "/illustrations/memory-leaf.png",
  memoryEmpty: "/illustrations/memory-empty.png",
  memoryArtExperience: "/illustrations/memory-art-1.png",
  memoryArtSubject: "/illustrations/memory-art-2.png",
  memoryArtEmotion: "/illustrations/memory-art-3.png",
  phqHeader: "/illustrations/phq-header.png",
  homeDashboard: "/illustrations/home-dashboard-2.svg",
} as const;

import {
  faHouseChimney,
  faBookBookmark,
  faHeadset,
  faCircleUser,
} from "@fortawesome/free-solid-svg-icons";

export const HouseChimney = createIcon(faHouseChimney);
export const Comments = createIcon(faComments);
export const BookBookmark = createIcon(faBookBookmark);
export const Headset = createIcon(faHeadset);
export const CircleUser = createIcon(faCircleUser);
export const Sliders = createIcon(faSliders);
// icon per top-level concept, shared by bottom nav, header, and dashboard
export const CONCEPT_ICONS: Record<string, any> = {
  beranda: HouseChimney,
  chat: Comments,
  confession: Mic,
  memori: BookBookmark,
  knowledgeGraph: Network,
  hotline: Headset,
  bantuan: HelpCircle,
  pengaturan: Sliders,
  profil: CircleUser,
};

export const MEMORY_TYPE_ICONS: Record<string, any> = {
  experience: Sprout,
  thought: Cloud,
  memory: Archive,
  emotion: Heart,
  topic: BookOpen,
  behaviour: PersonStanding,
  trigger: Zap,
};

export {
  faLanguage,
  faMicrophoneLines,
  faComments,
  faRightFromBracket,
  faEnvelopeCircleCheck,
  faSliders,
} from "@fortawesome/free-solid-svg-icons";

export type LucideIcon = React.ComponentType<any>;
