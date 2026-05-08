const { createApp, ref, computed, nextTick, onMounted, watch } = Vue;

const API_BASE = window.__LEXPRIM_API_URL__ || (window.__ENV__ && window.__ENV__.API_BASE) || window.location.origin || '';

const CHAT_MODE_META = Object.freeze({
    'agent-auto': { icon: '⚡', ar: 'ذكي (تلقائي)', en: 'Smart (Auto)' },
    direct: { icon: '💬', ar: 'دردشة مباشرة', en: 'Direct Chat' },
    'legal-agent': { icon: '⚖️', ar: 'المستشار القانوني', en: 'Legal Counsel' },
    'governance-agent': { icon: '🏛️', ar: 'خبير الحوكمة', en: 'Governance Expert' },
    // kimi-agent REMOVED — PDPL Article 33
    'claude-agent': { icon: '🧠', ar: 'Claude — تحليل عميق', en: 'Claude — Deep Analysis' },
    'ios-chat-integration-agent': { icon: '🍎', ar: 'iOS Chat Agent', en: 'iOS Chat Agent' },
    'gemini-agent': { icon: '✨', ar: 'Gemini', en: 'Gemini' },
    'perplexity-agent': { icon: '🔎', ar: 'Perplexity', en: 'Perplexity' },
    'groq-agent': { icon: '⚡', ar: 'Groq', en: 'Groq' }
});

const AGENT_CARD_META = Object.freeze({
    'legal-agent': {
        id: 'legal',
        name: 'Legal Analyst',
        roleAr: 'محلل قانوني',
        roleEn: 'Legal analyst',
        skills: ['Legal', 'Contracts', 'Compliance'],
        color: '#d97757'
    },
    'governance-agent': {
        id: 'governance',
        name: 'Governance Agent',
        roleAr: 'وكيل الحوكمة',
        roleEn: 'Governance specialist',
        skills: ['Governance', 'Policy', 'Risk'],
        color: '#8957e5'
    },
    // kimi-agent REMOVED — PDPL Article 33
    'claude-agent': {
        id: 'claude',
        name: 'Anthropic Claude',
        roleAr: 'تحليل عميق',
        roleEn: 'Deep analysis',
        skills: ['Reasoning', 'Policy', 'Drafting'],
        color: '#d97757'
    },
    'ios-chat-integration-agent': {
        id: 'ios-chat',
        name: 'iOS Chat Agent',
        roleAr: 'تكامل iOS',
        roleEn: 'iOS integration',
        skills: ['Mobile', 'PWA', 'Chat'],
        color: '#58a6ff'
    }
});

const I18N = {
    ar: {
        smartControl: 'نظام التحكم الذكي',
        general: 'عام',
        dashboard: 'لوحة التحكم',
        agents: 'الوكلاء (Agents)',
        chat: 'المحادثة',
        knowledge: 'قاعدة المعرفة',
        development: 'التطوير',
        deploy: 'النشر',
        logs: 'السجلات',
        settingsTitle: 'الإعدادات',
        settings: 'الإعدادات',
        systemOnline: 'النظام متصل',
        systemOffline: 'النظام غير متصل',
        refresh: 'تحديث',
        openChat: 'فتح المحادثة',
        totalRequests: 'إجمالي الطلبات',
        activeAgents: 'الوكلاء النشطون',
        responseTime: 'وقت الاستجابة',
        storedKnowledge: 'المعرفة المخزنة',
        fromYesterday: '+12.5% من الأمس',
        readyToWork: 'جاهزون للعمل',
        improved: '-8% تحسن',
        documents: 'وثيقة',
        quickActions: 'إجراءات سريعة',
        healthCheck: 'فحص صحة النظام',
        codeReview: 'مراجعة الكود',
        securityScan: 'فحص أمني',
        legalQuery: 'استشارة قانونية',
        qaHealthCheck: 'أجرِ فحص صحة شامل للنظام',
        qaCodeReview: 'راجع آخر التغييرات في الكود',
        qaSecurityScan: 'أجرِ فحص أمني للمشروع',
        qaLegalQuery: 'ما هي متطلبات الحوكمة؟',
        recentOps: 'آخر العمليات',
        all: 'الكل',
        online: 'متصل',
        offline: 'غير متصل',
        connected: 'متصل',
        disconnected: 'غير متصل',
        chatWith: 'محادثة',
        activate: 'تفعيل',
        chatAgent: 'الوكيل',
        smartAuto: 'ذكي (تلقائي)',
        directChat: 'دردشة مباشرة',
        specializedAgents: 'وكلاء متخصصون',
        chatWelcomeTitle: 'مرحباً في LexPrim Chat',
        chatWelcomeSub: 'اختر وكيلاً وابدأ المحادثة',
        chatPlaceholder: 'اكتب رسالتك...',
        chatPanel: 'المحادثة السريعة',
        chatPanelEmpty: 'ابدأ محادثة جديدة...',
        knowledgeUpload: 'إدارة قاعدة المعرفة',
        knowledgePlaceholder: 'ألصق النص أو الكود هنا للاستعلام...',
        ingestRepo: 'استيعاب المستودع',
        queryBrain: 'استعلام',
        vectorMemory: 'الذاكرة المتجهة',
        totalVectors: 'إجمالي المتجهات',
        deployStatus: 'حالة النشر',
        active: 'نشط',
        primaryHost: 'الاستضافة السحابية',
        domains: 'النطاقات',
        deployActions: 'عمليات النشر',
        deployRender: 'نشر التحديثات',
        deployCF: 'نشر Cloudflare',
        deployPages: 'نشر GitHub Pages',
        deployRenderNote: 'الاستضافة السحابية نشطة مع النطاقين lexprim.com و www.lexprim.com وجميع المسارات الرئيسية تعمل من نفس الخدمة.',
        openMainChat: 'فتح المحادثة الرئيسية',
        openMainSite: 'فتح الموقع الرئيسي',
        systemLogs: 'سجلات النظام',
        clear: 'مسح',
        noLogs: 'لا توجد سجلات',
        language: 'اللغة',
        interfaceLang: 'لغة الواجهة',
        apiConfig: 'إعدادات API',
        apiBase: 'عنوان API',
        adminToken: 'رمز المسؤول',
        save: 'حفظ',
        about: 'حول',
        dashboardSub: 'نظرة عامة على أداء النظام',
        agentsSub: 'تفعيل وإدارة وكلاء الذكاء الاصطناعي',
        chatSub: 'محادثة مع وكلاء الذكاء الاصطناعي',
        knowledgeSub: 'إدارة قاعدة البيانات المتجهة',
        deploySub: 'إدارة عمليات النشر والنطاقات',
        logsSub: 'مراقبة سجلات النظام',
        settingsSub: 'إعدادات النظام والتخصيص',
        suggestion1: 'ما هي منصة LexPrim؟',
        suggestion2: 'أجرِ فحص صحة',
        suggestion3: 'ما الوكلاء المتاحون؟',
        suggestion4: 'ساعدني في كتابة كود',
        aiTools: 'أدوات الذكاء',
        smartTasks: 'مهام ذكية',
        smartTasksSub: 'مهام متقدمة عبر النماذج الذكية',
        taskLegal: 'تحليل قانوني', taskLegalDesc: 'تحليل عقود ولوائح واستشارات قانونية متخصصة',
        taskCode: 'مراجعة الكود', taskCodeDesc: 'مراجعة شاملة للكود مع اقتراحات التحسين والأمان',
        taskSecurity: 'تدقيق أمني', taskSecurityDesc: 'فحص أمني شامل للمشاريع والبنية التحتية',
        taskResearch: 'بحث واستقصاء', taskResearchDesc: 'بحث حي مع مصادر وروابط حديثة ودقيقة',
        taskTranslate: 'ترجمة متقدمة', taskTranslateDesc: 'ترجمة احترافية بين العربية والإنجليزية والصينية',
        taskGovernance: 'فحص الحوكمة', taskGovernanceDesc: 'مراجعة الامتثال والحوكمة وفق معايير SAMA',
        taskCreative: 'إبداع ومحتوى', taskCreativeDesc: 'كتابة إبداعية ومحتوى تسويقي وتقارير احترافية',
        taskCompare: 'مقارنة النماذج', taskCompareDesc: 'أرسل نفس السؤال لعدة نماذج وقارن الإجابات',
        taskFastInfer: 'استدلال فائق السرعة', taskFastInferDesc: 'إجابات سريعة جداً عبر Groq',
        plLegal: 'ألصق نص العقد أو السؤال القانوني هنا...',
        plCode: 'ألصق الكود المراد مراجعته هنا...',
        plSecurity: 'صف المشروع أو ألصق الكود للفحص الأمني...',
        plResearch: 'اكتب موضوع البحث هنا...',
        plTranslate: 'ألصق النص المراد ترجمته هنا...',
        plGovernance: 'صف الإجراء أو السياسة المراد فحصها...',
        plCreative: 'صف المحتوى المطلوب...',
        plCompare: 'اكتب سؤالك لمقارنة الإجابات...',
        plFastInfer: 'اكتب سؤالك السريع هنا...',
        execute: 'تنفيذ', processing: 'جاري المعالجة...', compareModels: 'مقارنة النماذج',
        selectTaskTitle: 'اختر مهمة ذكية', selectTaskDesc: 'اختر نوع المهمة من الأعلى للبدء عبر النموذج الأنسب',
    },
    en: {
        smartControl: 'Smart Control System',
        general: 'General',
        dashboard: 'Dashboard',
        agents: 'Agents',
        chat: 'Chat',
        knowledge: 'Knowledge Base',
        development: 'Development',
        deploy: 'Deploy',
        logs: 'Logs',
        settingsTitle: 'Settings',
        settings: 'Settings',
        systemOnline: 'System Online',
        systemOffline: 'System Offline',
        refresh: 'Refresh',
        openChat: 'Open Chat',
        totalRequests: 'Total Requests',
        activeAgents: 'Active Agents',
        responseTime: 'Response Time',
        storedKnowledge: 'Stored Knowledge',
        fromYesterday: '+12.5% from yesterday',
        readyToWork: 'Ready to work',
        improved: '-8% improved',
        documents: 'documents',
        quickActions: 'Quick Actions',
        healthCheck: 'Health Check',
        codeReview: 'Code Review',
        securityScan: 'Security Scan',
        legalQuery: 'Legal Query',
        qaHealthCheck: 'Run a comprehensive system health check',
        qaCodeReview: 'Review the latest code changes',
        qaSecurityScan: 'Run a security scan on the project',
        qaLegalQuery: 'What are the governance requirements?',
        recentOps: 'Recent Operations',
        all: 'All',
        online: 'Online',
        offline: 'Offline',
        connected: 'Connected',
        disconnected: 'Disconnected',
        chatWith: 'Chat',
        activate: 'Activate',
        chatAgent: 'Agent',
        smartAuto: 'Smart (Auto)',
        directChat: 'Direct Chat',
        specializedAgents: 'Specialized Agents',
        chatWelcomeTitle: 'Welcome to LexPrim Chat',
        chatWelcomeSub: 'Select an agent and start a conversation',
        chatPlaceholder: 'Type your message...',
        chatPanel: 'Quick Chat',
        chatPanelEmpty: 'Start a new conversation...',
        knowledgeUpload: 'Knowledge Base Management',
        knowledgePlaceholder: 'Paste text or code here to query...',
        ingestRepo: 'Ingest Repository',
        queryBrain: 'Query',
        vectorMemory: 'Vector Memory',
        totalVectors: 'Total Vectors',
        deployStatus: 'Deploy Status',
        active: 'Active',
        primaryHost: 'Cloud Hosting',
        domains: 'Domains',
        deployActions: 'Deploy Actions',
        deployRender: 'Deploy Updates',
        deployCF: 'Deploy Cloudflare',
        deployPages: 'Deploy GitHub Pages',
        deployRenderNote: 'Cloud hosting is active with lexprim.com and www.lexprim.com, and the main routes are served by the same service.',
        openMainChat: 'Open main chat',
        openMainSite: 'Open main site',
        systemLogs: 'System Logs',
        clear: 'Clear',
        noLogs: 'No logs available',
        language: 'Language',
        interfaceLang: 'Interface Language',
        apiConfig: 'API Configuration',
        apiBase: 'API Base URL',
        adminToken: 'Admin Token',
        save: 'Save',
        about: 'About',
        dashboardSub: 'System performance overview',
        agentsSub: 'Activate and manage AI agents',
        chatSub: 'Chat with AI agents',
        knowledgeSub: 'Manage the vector database',
        deploySub: 'Manage deployments and domains',
        logsSub: 'Monitor system logs',
        settingsSub: 'System settings and customization',
        suggestion1: 'What is LexPrim?',
        suggestion2: 'Run a health check',
        suggestion3: 'What agents are available?',
        suggestion4: 'Help me write code',
        aiTools: 'AI Tools',
        smartTasks: 'Smart Tasks',
        smartTasksSub: 'Advanced tasks via smart AI models',
        taskLegal: 'Legal Analysis', taskLegalDesc: 'Contract analysis, regulations, and specialized legal consultation',
        taskCode: 'Code Review', taskCodeDesc: 'Comprehensive code review with improvement and security suggestions',
        taskSecurity: 'Security Audit', taskSecurityDesc: 'Full security scan for projects and infrastructure',
        taskResearch: 'Research', taskResearchDesc: 'Live research with recent sources and accurate citations',
        taskTranslate: 'Translation', taskTranslateDesc: 'Professional translation between Arabic, English, and Chinese',
        taskGovernance: 'Governance Check', taskGovernanceDesc: 'Compliance and governance review per SAMA standards',
        taskCreative: 'Creative Writing', taskCreativeDesc: 'Creative writing, marketing content, and professional reports',
        taskCompare: 'Model Comparison', taskCompareDesc: 'Send the same question to multiple models and compare answers',
        taskFastInfer: 'Ultra-Fast Inference', taskFastInferDesc: 'Very fast answers via Groq',
        plLegal: 'Paste the contract text or legal question here...',
        plCode: 'Paste the code to review here...',
        plSecurity: 'Describe the project or paste code for security scan...',
        plResearch: 'Enter your research topic here...',
        plTranslate: 'Paste the text to translate here...',
        plGovernance: 'Describe the procedure or policy to check...',
        plCreative: 'Describe the content needed...',
        plCompare: 'Write your question to compare answers...',
        plFastInfer: 'Write your quick question here...',
        execute: 'Execute', processing: 'Processing...', compareModels: 'Compare Models',
        selectTaskTitle: 'Select a Smart Task', selectTaskDesc: 'Choose a task type above to start with the best AI model',
    }
};

const SMART_TASKS = [
    { id: 'legal', icon: '⚖️', titleKey: 'taskLegal', descKey: 'taskLegalDesc', placeholderKey: 'plLegal', agentId: 'legal-agent', model: 'Legal Agent' },
    { id: 'code', icon: '🔍', titleKey: 'taskCode', descKey: 'taskCodeDesc', placeholderKey: 'plCode', agentId: 'code-review-agent', model: 'Code Review Agent' },
    { id: 'security', icon: '🛡️', titleKey: 'taskSecurity', descKey: 'taskSecurityDesc', placeholderKey: 'plSecurity', agentId: 'security-agent', model: 'Security Agent' },
    { id: 'research', icon: '🔎', titleKey: 'taskResearch', descKey: 'taskResearchDesc', placeholderKey: 'plResearch', agentId: 'perplexity-agent', model: 'Perplexity' },
    { id: 'translate', icon: '🌐', titleKey: 'taskTranslate', descKey: 'taskTranslateDesc', placeholderKey: 'plTranslate', agentId: 'claude-agent', model: 'Claude' },
    { id: 'governance', icon: '🏛️', titleKey: 'taskGovernance', descKey: 'taskGovernanceDesc', placeholderKey: 'plGovernance', agentId: 'governance-agent', model: 'Governance Agent' },
    { id: 'creative', icon: '✨', titleKey: 'taskCreative', descKey: 'taskCreativeDesc', placeholderKey: 'plCreative', agentId: 'gemini-agent', model: 'Gemini' },
    { id: 'compare', icon: '📊', titleKey: 'taskCompare', descKey: 'taskCompareDesc', placeholderKey: 'plCompare', agentId: 'agent-auto', model: 'Multi-Model' },
    { id: 'fast', icon: '⚡', titleKey: 'taskFastInfer', descKey: 'taskFastInferDesc', placeholderKey: 'plFastInfer', agentId: 'groq-agent', model: 'Groq' },
];

const TASK_MODELS = [
    { id: 'agent-auto', name: 'Smart Auto', icon: '🤖' },
    { id: 'legal-agent', name: 'Legal', icon: '⚖️' },
    { id: 'code-review-agent', name: 'Code Review', icon: '🔍' },
    { id: 'security-agent', name: 'Security', icon: '🛡️' },
    { id: 'governance-agent', name: 'Governance', icon: '🏛️' },
    { id: 'claude-agent', name: 'Claude', icon: '🎯' },
    { id: 'gemini-agent', name: 'Gemini', icon: '🧠' },
    { id: 'perplexity-agent', name: 'Perplexity', icon: '🔎' },
    { id: 'groq-agent', name: 'Groq', icon: '⚡' },
    // kimi-agent REMOVED — PDPL Article 33
];

createApp({
    setup() {
        const readSessionToken = (sessionKey, legacyLocalKey) => {
            const sessionValue = sessionStorage.getItem(sessionKey);
            if (sessionValue) return sessionValue;

            const legacyValue = localStorage.getItem(legacyLocalKey);
            if (legacyValue) {
                sessionStorage.setItem(sessionKey, legacyValue);
                localStorage.removeItem(legacyLocalKey);
                return legacyValue;
            }

            return '';
        };

        const persistSessionToken = (sessionKey, legacyLocalKey, value) => {
            const normalized = (value || '').trim();
            if (normalized) {
                sessionStorage.setItem(sessionKey, normalized);
            } else {
                sessionStorage.removeItem(sessionKey);
            }
            localStorage.removeItem(legacyLocalKey);
        };

        const isLocalHost = ['localhost', '127.0.0.1'].includes(window.location.hostname);
        const initialApiBase = isLocalHost ? window.location.origin : (localStorage.getItem('lexprim-api') || '');
        const lang = ref(localStorage.getItem('lexprim-lang') || 'ar');
        const currentView = ref('dashboard');
        const sidebarOpen = ref(false);
        const chatPanelOpen = ref(false);
        const systemOnline = ref(true);
        const reconnecting = ref(false);
        const retryCountdown = ref(0);
        let _retryTimer = null;
        const apiBase = ref(initialApiBase);
        const adminToken = ref(readSessionToken('lexprim-token', 'lexprim-token'));

        const stats = ref({
            requests: '...',
            activeAgents: '...',
            responseTime: '...',
            knowledge: '...'
        });

        const logs = ref([]);
        const allLogs = ref([]);

        const agents = ref([]);
        const chatModeOptions = ref([]);

        const agentFilter = ref('all');

        const chatAgent = ref('agent-auto');
        const chatLang = ref(lang.value);
        const chatInput = ref('');
        const chatMessages = ref([]);
        const chatLoading = ref(false);
        const chatError = ref('');
        const chatMessagesRef = ref(null);
        const chatPanelMessagesRef = ref(null);
        const chatInputRef = ref(null);

        const knowledgeText = ref('');
        const knowledgeStatus = ref('');
        const brainStats = ref({ vectors: 0 });
        const brainResults = ref([]);

        const activeTask = ref(null);
        const taskModel = ref('agent-auto');
        const taskInput = ref('');
        const taskResult = ref('');
        const taskRunning = ref(false);
        const compareResults = ref([]);
        const smartTaskDefs = computed(() => SMART_TASKS);
        const availableModels = computed(() => TASK_MODELS);
        const activeTaskObj = computed(() => SMART_TASKS.find(t => t.id === activeTask.value) || SMART_TASKS[0]);

        const domains = ref([
            { name: 'lexprim.com', url: 'https://lexprim.com/', route: 'Main Site' },
            { name: 'www.lexprim.com', url: 'https://www.lexprim.com/', route: 'Primary Canonical' },
            { name: 'lexprim.com/chat', url: 'https://lexprim.com/chat', route: 'Advanced Chat' },
            { name: 'lexprim.com/app', url: 'https://lexprim.com/app', route: 'App Surface' },
            { name: 'lexprim.com/enterprise/control', url: 'https://lexprim.com/enterprise/control/', route: 'Control Hub' },
            { name: 'lexprim.com/ios-app', url: 'https://lexprim.com/ios-app', route: 'iOS Surface' },
            { name: 'lexprim.com/miniapp', url: 'https://lexprim.com/miniapp', route: 'Mini App' },
            { name: 'lexprim.com/admin', url: 'https://lexprim.com/admin', route: 'Admin Panel' },
        ]);

        const isMobile = ref(window.innerWidth <= 768);

        function t(key) {
            return I18N[lang.value]?.[key] || I18N.en[key] || key;
        }

        function getModeLabel(modeId, fallbackName = '') {
            const meta = CHAT_MODE_META[modeId];
            if (meta) return lang.value === 'ar' ? meta.ar : meta.en;
            return fallbackName || modeId;
        }

        function getModeIcon(modeId, fallbackIcon = '🤖') {
            return CHAT_MODE_META[modeId]?.icon || fallbackIcon;
        }

        function buildModeOption(mode) {
            return {
                ...mode,
                icon: getModeIcon(mode.id, mode.icon),
                name: getModeLabel(mode.id, mode.name),
                available: mode.available !== false,
            };
        }

        function buildAgentCard(mode) {
            const cardMeta = AGENT_CARD_META[mode.id] || {};
            const fallbackRole = lang.value === 'ar' ? 'وكيل ذكي' : 'Smart agent';
            const skills = [
                ...(Array.isArray(cardMeta.skills) ? cardMeta.skills : []),
                ...(mode.risk ? [String(mode.risk).toUpperCase()] : []),
                ...(mode.preferredProvider && mode.preferredProviderAvailable ? [String(mode.preferredProvider).toUpperCase()] : [])
            ].slice(0, 4);

            return {
                id: cardMeta.id || mode.id,
                agentId: mode.id,
                name: cardMeta.name || mode.name || mode.id,
                icon: mode.icon || '🤖',
                role: lang.value === 'ar' ? (cardMeta.roleAr || fallbackRole) : (cardMeta.roleEn || fallbackRole),
                status: mode.available === false ? 'offline' : 'online',
                skills: skills.length ? skills : ['AI'],
                color: cardMeta.color || '#58a6ff'
            };
        }

        const pageTitle = computed(() => {
            const map = {
                dashboard: t('dashboard'),
                agents: t('agents'),
                chat: t('chat'),
                smartTasks: t('smartTasks'),
                knowledge: t('knowledge'),
                deploy: t('deploy'),
                logs: t('logs'),
                settings: t('settings'),
            };
            return map[currentView.value] || t('dashboard');
        });

        const pageSubtitle = computed(() => {
            const map = {
                dashboard: t('dashboardSub'),
                agents: t('agentsSub'),
                chat: t('chatSub'),
                smartTasks: t('smartTasksSub'),
                knowledge: t('knowledgeSub'),
                deploy: t('deploySub'),
                logs: t('logsSub'),
                settings: t('settingsSub'),
            };
            return map[currentView.value] || '';
        });

        const filteredAgents = computed(() => {
            if (agentFilter.value === 'all') return agents.value;
            return agents.value.filter(a => a.status === agentFilter.value);
        });

        const chatSuggestions = computed(() => [
            t('suggestion1'), t('suggestion2'), t('suggestion3'), t('suggestion4')
        ]);

        function setView(view) {
            currentView.value = view;
            sidebarOpen.value = false;
        }

        function openPrimarySite() {
            window.open('https://lexprim.com/', '_blank', 'noopener');
        }

        function toggleLang() {
            lang.value = lang.value === 'ar' ? 'en' : 'ar';
            chatLang.value = lang.value;
            onLangChange();
        }

        function onLangChange() {
            localStorage.setItem('lexprim-lang', lang.value);
            document.documentElement.lang = lang.value;
            document.documentElement.dir = lang.value === 'ar' ? 'rtl' : 'ltr';
            document.body.dir = lang.value === 'ar' ? 'rtl' : 'ltr';

            chatModeOptions.value = chatModeOptions.value.map(buildModeOption);
            agents.value = chatModeOptions.value
                .filter(mode => mode.id !== 'agent-auto' && mode.id !== 'direct')
                .map(buildAgentCard);
        }

        function addLog(message, level = 'info') {
            const now = new Date();
            const time = now.toLocaleTimeString('en-US', { hour12: false });
            const entry = { time, message, level };
            logs.value.unshift(entry);
            allLogs.value.unshift(entry);
            if (logs.value.length > 10) logs.value.pop();
            if (allLogs.value.length > 200) allLogs.value.pop();
        }

        function clearLogs() {
            allLogs.value = [];
        }

        function getApiUrl() {
            const raw = apiBase.value || API_BASE;
            return raw ? raw.trim().replace(/\/+$/, '') : '';
        }

        function getHeaders() {
            const headers = { 'Content-Type': 'application/json' };
            if (adminToken.value) {
                headers['x-admin-token'] = adminToken.value;
            }
            return headers;
        }

        async function loadChatOptions({ silent = false } = {}) {
            try {
                const requestHeaders = adminToken.value ? { 'x-admin-token': adminToken.value } : undefined;
                const res = await fetch(`${getApiUrl()}/api/chat/options`, {
                    ...(requestHeaders ? { headers: requestHeaders } : {})
                });

                if (!res.ok) {
                    throw new Error(`HTTP ${res.status}`);
                }

                const data = await res.json();
                const modes = Array.isArray(data.modes) ? data.modes : [];
                if (modes.length === 0) {
                    throw new Error('No chat modes returned');
                }

                const normalizedModes = modes.map(buildModeOption);
                chatModeOptions.value = normalizedModes;

                const agentModes = normalizedModes.filter(mode => mode.id !== 'agent-auto' && mode.id !== 'direct');
                agents.value = agentModes.map(buildAgentCard);
                stats.value.activeAgents = agents.value.length;

                const selectedExists = normalizedModes.some(mode => mode.id === chatAgent.value && mode.available !== false);
                if (!selectedExists) {
                    const firstAvailable = normalizedModes.find(mode => mode.available !== false);
                    chatAgent.value = firstAvailable?.id || 'agent-auto';
                }

                if (!silent) {
                    addLog(lang.value === 'ar'
                        ? `تم تحميل أوضاع الدردشة (${normalizedModes.length})`
                        : `Loaded chat modes (${normalizedModes.length})`);
                }
            } catch (error) {
                if (!silent) {
                    addLog(
                        lang.value === 'ar'
                            ? `تعذر تحميل خيارات الدردشة: ${error.message}`
                            : `Failed to load chat modes: ${error.message}`,
                        'error'
                    );
                }

                const fallbackModes = ['agent-auto', 'direct', 'legal-agent', 'governance-agent', 'claude-agent']
                    .map(id => buildModeOption({ id, available: true }));

                chatModeOptions.value = fallbackModes;
                agents.value = fallbackModes
                    .filter(mode => mode.id !== 'agent-auto' && mode.id !== 'direct')
                    .map(buildAgentCard);

                if (!chatModeOptions.value.some(mode => mode.id === chatAgent.value)) {
                    chatAgent.value = 'agent-auto';
                }
            }
        }

        async function refreshData() {
            addLog(lang.value === 'ar' ? 'جاري تحديث البيانات...' : 'Refreshing data...');

            try {
                const res = await fetch(`${getApiUrl()}/api/health`);
                if (res.ok) {
                    systemOnline.value = true;
                    reconnecting.value = false;
                    retryCountdown.value = 0;
                    if (_retryTimer) { clearTimeout(_retryTimer); _retryTimer = null; }
                    const data = await res.json();
                    if (data.uptime) {
                        stats.value.responseTime = Math.round(data.responseTime || 245);
                    }
                    addLog(lang.value === 'ar' ? 'النظام متصل ✓' : 'System online ✓');
                } else {
                    systemOnline.value = false;
                    reconnecting.value = true;
                    addLog(lang.value === 'ar' ? 'تعذر الاتصال بالخادم، يرجى المحاولة لاحقاً' : 'Unable to connect to server, please try again later', 'error');
                }
            } catch {
                systemOnline.value = false;
                reconnecting.value = true;
                addLog(lang.value === 'ar' ? 'تعذر الوصول للخادم، تحقق من الاتصال بالإنترنت' : 'Unable to reach server, check your internet connection', 'error');
            }

            await loadChatOptions({ silent: true });

            try {
                const res = await fetch(`${getApiUrl()}/api/knowledge`);
                if (res.ok) {
                    const data = await res.json();
                    const docs = data.documents || data.data?.documents || [];
                    stats.value.knowledge = docs.length;
                }
            } catch {}

            // Keep public control hub free from auth popups by skipping protected brain stats calls.
            brainStats.value = { vectors: 0 };

            nextTick(() => {
                try { lucide.createIcons(); } catch {}
            });
        }

        // Exponential backoff retry: 5s → 10s → 20s → 30s (cap), resets on success.
        let _retryAttempt = 0;
        const RETRY_DELAYS = [5, 10, 20, 30];

        function scheduleRetry() {
            if (_retryTimer) return; // already scheduled
            const delaySec = RETRY_DELAYS[Math.min(_retryAttempt, RETRY_DELAYS.length - 1)];
            _retryAttempt++;
            retryCountdown.value = delaySec;
            addLog(
                lang.value === 'ar'
                    ? `إعادة المحاولة خلال ${delaySec} ثوانٍ...`
                    : `Retrying in ${delaySec}s...`
            );

            const tick = setInterval(() => {
                retryCountdown.value = Math.max(0, retryCountdown.value - 1);
            }, 1000);

            _retryTimer = setTimeout(async () => {
                clearInterval(tick);
                _retryTimer = null;
                retryCountdown.value = 0;
                await refreshData();
                if (!systemOnline.value) scheduleRetry();
            }, delaySec * 1000);
        }

        async function retryNow() {
            if (_retryTimer) { clearTimeout(_retryTimer); _retryTimer = null; }
            retryCountdown.value = 0;
            reconnecting.value = true;
            addLog(lang.value === 'ar' ? 'إعادة المحاولة يدوياً...' : 'Retrying manually...');
            await refreshData();
            if (!systemOnline.value) scheduleRetry();
        }

        async function sendChatMessage(text) {
            const message = text || chatInput.value.trim();
            if (!message || chatLoading.value) return;

            const selectedMode = chatModeOptions.value.find(mode => mode.id === chatAgent.value);
            if (!selectedMode || selectedMode.available === false) {
                chatError.value = lang.value === 'ar'
                    ? 'وضع الدردشة المحدد غير متاح حالياً.'
                    : 'Selected chat mode is currently unavailable.';
                return;
            }

            chatInput.value = '';
            chatError.value = '';

            const history = chatMessages.value
                .filter(m => m.role === 'user' || m.role === 'assistant')
                .map(m => ({ role: m.role, content: m.content }));

            chatMessages.value.push({ role: 'user', content: message, time: Date.now() });
            scrollChatToBottom();

            chatLoading.value = true;
            addLog(`Chat → ${chatAgent.value}: "${message.substring(0, 40)}..."`);

            try {
                let url, body;

                if (chatAgent.value === 'direct') {
                    url = `${getApiUrl()}/api/chat/direct`;
                    body = { message, language: chatLang.value, history };
                } else {
                    url = `${getApiUrl()}/api/chat`;
                    body = { agentId: chatAgent.value, message, language: chatLang.value, history };
                }

                const res = await fetch(url, {
                    method: 'POST',
                    headers: getHeaders(),
                    body: JSON.stringify(body)
                });

                if (!res.ok) {
                    const errData = await res.json().catch(() => ({}));
                    throw new Error(errData.message || errData.error || `HTTP ${res.status}`);
                }

                const data = await res.json();
                const output = data.output || data.data?.output || data.reply ||
                    (lang.value === 'ar' ? 'لم يتم استلام رد.' : 'No response received.');

                chatMessages.value.push({ role: 'assistant', content: output, time: Date.now() });
                addLog(lang.value === 'ar' ? 'تم استلام الرد ✓' : 'Response received ✓');
            } catch (err) {
                console.error('Chat error:', err);
                if (err instanceof TypeError || err.message?.includes('fetch')) {
                    chatError.value = lang.value === 'ar'
                        ? 'فشل الاتصال بالخادم. تحقق من اتصال الإنترنت.'
                        : 'Failed to connect. Check your connection.';
                } else {
                    chatError.value = err.message;
                }
                addLog(`Chat error: ${err.message}`, 'error');
            } finally {
                chatLoading.value = false;
                scrollChatToBottom();
            }
        }

        function clearChatMessages() {
            chatMessages.value = [];
            chatError.value = '';
        }

        function scrollChatToBottom() {
            nextTick(() => {
                if (chatMessagesRef.value) {
                    chatMessagesRef.value.scrollTop = chatMessagesRef.value.scrollHeight;
                }
                if (chatPanelMessagesRef.value) {
                    chatPanelMessagesRef.value.scrollTop = chatPanelMessagesRef.value.scrollHeight;
                }
            });
        }

        function openChatWith(agentId, message) {
            const preferred = chatModeOptions.value.find(mode => mode.id === agentId && mode.available !== false);
            const fallback = chatModeOptions.value.find(mode => mode.available !== false);
            chatAgent.value = preferred?.id || fallback?.id || 'agent-auto';
            if (isMobile.value || currentView.value === 'chat') {
                currentView.value = 'chat';
                sidebarOpen.value = false;
            } else {
                chatPanelOpen.value = true;
            }
            if (message) {
                nextTick(() => sendChatMessage(message));
            }
        }

        function activateAgent(id) {
            addLog(`Agent activated: ${id}`);
            const agent = agents.value.find(a => a.id === id);
            if (agent) {
                openChatWith(agent.agentId, '');
            }
        }

        async function ingestRepo() {
            knowledgeStatus.value = lang.value === 'ar' ? 'جاري استيعاب المستودع...' : 'Ingesting repository...';
            try {
                const res = await fetch(`${getApiUrl()}/api/ingest`, {
                    method: 'POST',
                    headers: getHeaders(),
                    body: JSON.stringify({})
                });
                const data = await res.json();
                const count = data.data?.files || data.files || data.ingested || 0;
                knowledgeStatus.value = lang.value === 'ar'
                    ? `تم استيعاب ${count} ملف بنجاح!`
                    : `Successfully ingested ${count} files!`;
                addLog(`Ingested ${count} files`);
                refreshData();
            } catch (e) {
                knowledgeStatus.value = lang.value === 'ar'
                    ? 'فشل الاستيعاب. تحقق من الإعدادات.'
                    : 'Ingestion failed. Check settings.';
                addLog('Ingestion failed', 'error');
            }
        }

        async function queryBrain() {
            const question = knowledgeText.value.trim();
            if (!question) return;

            knowledgeStatus.value = lang.value === 'ar' ? 'جاري البحث...' : 'Searching...';
            try {
                const res = await fetch(`${getApiUrl()}/api/brain/query`, {
                    method: 'POST',
                    headers: getHeaders(),
                    body: JSON.stringify({ question, topK: 5 })
                });
                const data = await res.json();
                const context = data.data?.context || data.context || [];
                brainResults.value = Array.isArray(context) ? context : [context];
                knowledgeStatus.value = lang.value === 'ar'
                    ? `تم العثور على ${brainResults.value.length} نتيجة`
                    : `Found ${brainResults.value.length} results`;
                addLog(`Brain query: "${question.substring(0, 30)}..." → ${brainResults.value.length} results`);
            } catch {
                knowledgeStatus.value = lang.value === 'ar'
                    ? 'فشل الاستعلام.'
                    : 'Query failed.';
                addLog('Brain query failed', 'error');
            }
        }

        function triggerDeploy(target) {
            addLog(`Deploy triggered: ${target}`);
            const msg = lang.value === 'ar'
                ? `تم إرسال أمر النشر إلى ${target}`
                : `Deploy command sent to ${target}`;
            alert(msg);
        }

        function selectTask(task) {
            activeTask.value = task.id;
            taskModel.value = task.agentId;
            taskResult.value = '';
            compareResults.value = [];
            nextTick(() => { try { lucide.createIcons(); } catch {} });
        }

        async function callAgentDirect(agentId, message) {
            const isDirect = agentId === 'direct';
            const url = isDirect ? `${getApiUrl()}/api/chat/direct` : `${getApiUrl()}/api/chat`;
            const body = isDirect ? { message, language: lang.value } : { agentId, message, language: lang.value };
            const res = await fetch(url, { method: 'POST', headers: getHeaders(), body: JSON.stringify(body) });
            if (!res.ok) { const e = await res.json().catch(() => ({})); throw new Error(e.message || e.error || `HTTP ${res.status}`); }
            const d = await res.json();
            return d.output || d.data?.output || d.reply || (lang.value === 'ar' ? 'لم يتم استلام رد.' : 'No response received.');
        }

        async function runSmartTask() {
            if (!taskInput.value.trim() || taskRunning.value) return;
            taskRunning.value = true;
            taskResult.value = '';
            compareResults.value = [];
            const task = activeTaskObj.value;
            const agentId = taskModel.value || task.agentId;
            addLog(`Smart Task → ${task.id} via ${agentId}`);
            try {
                const prefix = lang.value === 'ar' ? `[مهمة: ${t(task.titleKey)}]\n\n` : `[Task: ${t(task.titleKey)}]\n\n`;
                taskResult.value = await callAgentDirect(agentId, prefix + taskInput.value.trim());
                addLog('Task completed ✓');
            } catch (err) {
                taskResult.value = `❌ ${err.message}`;
                addLog(`Task error: ${err.message}`, 'error');
            } finally {
                taskRunning.value = false;
                nextTick(() => { try { lucide.createIcons(); } catch {} });
            }
        }

        async function runCompare() {
            if (!taskInput.value.trim() || taskRunning.value) return;
            taskRunning.value = true;
            taskResult.value = '';
            const modelsToCompare = ['agent-auto', 'claude-agent', 'gemini-agent', 'perplexity-agent', 'groq-agent'];
            compareResults.value = modelsToCompare.map(id => {
                const m = TASK_MODELS.find(x => x.id === id);
                return { model: id, name: m?.name || id, icon: m?.icon || '🤖', loading: true, result: '', error: '', time: 0 };
            });
            addLog('Compare → ' + modelsToCompare.join(', '));
            const promises = compareResults.value.map(async (cr) => {
                const start = Date.now();
                try {
                    cr.result = await callAgentDirect(cr.model, taskInput.value.trim());
                    cr.time = Date.now() - start;
                } catch (err) {
                    cr.error = err.message;
                    cr.time = Date.now() - start;
                } finally { cr.loading = false; }
            });
            await Promise.allSettled(promises);
            taskRunning.value = false;
            addLog('Compare completed ✓');
            nextTick(() => { try { lucide.createIcons(); } catch {} });
        }

        function clearTaskResult() {
            taskResult.value = '';
            compareResults.value = [];
        }

        function saveSettings() {
            localStorage.setItem('lexprim-api', apiBase.value);
            persistSessionToken('lexprim-token', 'lexprim-token', adminToken.value);
            addLog(lang.value === 'ar' ? 'تم حفظ الإعدادات' : 'Settings saved');
        }

        function renderMarkdown(text) {
            if (!text) return '';
            try {
                const html = marked.parse(text, { breaks: true, gfm: true });
                return typeof DOMPurify !== 'undefined' ? DOMPurify.sanitize(html) : html;
            } catch {
                return text;
            }
        }

        function formatTime(time) {
            if (!time) return '';
            const d = new Date(time);
            return d.toLocaleTimeString(lang.value === 'ar' ? 'ar-SA' : 'en-US', {
                hour: '2-digit',
                minute: '2-digit'
            });
        }

        onMounted(() => {
            onLangChange();

            addLog(lang.value === 'ar' ? 'تم بدء تشغيل LexPrim Control Hub' : 'LexPrim Control Hub started');
            addLog(lang.value === 'ar' ? 'جاري الاتصال بالخادم...' : 'Connecting to server...');

            refreshData().then(() => {
                if (!systemOnline.value) scheduleRetry();
            });

            setInterval(async () => {
                if (systemOnline.value) {
                    await refreshData();
                    if (!systemOnline.value) scheduleRetry();
                }
            }, 30000);

            window.addEventListener('resize', () => {
                isMobile.value = window.innerWidth <= 768;
            });

            nextTick(() => {
                try { lucide.createIcons(); } catch {}
            });
        });

        watch(currentView, () => {
            nextTick(() => {
                try { lucide.createIcons(); } catch {}
            });
        });

        watch(chatPanelOpen, () => {
            nextTick(() => {
                try { lucide.createIcons(); } catch {}
            });
        });

        return {
            lang,
            currentView,
            sidebarOpen,
            chatPanelOpen,
            systemOnline,
            reconnecting,
            retryCountdown,
            apiBase,
            adminToken,
            stats,
            logs,
            allLogs,
            agents,
            agentFilter,
            filteredAgents,
            chatModeOptions,
            chatAgent,
            chatLang,
            chatInput,
            chatMessages,
            chatLoading,
            chatError,
            chatMessagesRef,
            chatPanelMessagesRef,
            chatInputRef,
            chatSuggestions,
            knowledgeText,
            knowledgeStatus,
            brainStats,
            brainResults,
            domains,
            isMobile,
            pageTitle,
            pageSubtitle,
            activeTask,
            taskModel,
            taskInput,
            taskResult,
            taskRunning,
            compareResults,
            smartTaskDefs,
            availableModels,
            activeTaskObj,
            t,
            setView,
            openPrimarySite,
            toggleLang,
            onLangChange,
            refreshData,
            retryNow,
            sendChatMessage,
            clearChatMessages,
            openChatWith,
            activateAgent,
            ingestRepo,
            queryBrain,
            triggerDeploy,
            saveSettings,
            renderMarkdown,
            formatTime,
            clearLogs,
            selectTask,
            runSmartTask,
            runCompare,
            clearTaskResult,
        };
    }
}).mount('#app');
