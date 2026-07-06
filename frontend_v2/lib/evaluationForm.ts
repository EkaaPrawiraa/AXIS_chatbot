const FALLBACK_EVALUATION_FORM_URL = 'https://forms.gle/xnUW8fkeuxaRwKTC7';

const configured = process.env.NEXT_PUBLIC_EVALUATION_FORM_URL;

export const evaluationFormUrl =
  configured && configured !== 'https://forms.gle/REPLACE_ME' ? configured : FALLBACK_EVALUATION_FORM_URL;
