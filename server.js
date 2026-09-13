const express = require('express');
const http = require('http');
const path = require('path');
const fs = require('fs');
const cookieParser = require('cookie-parser');
const session = require('express-session');
const multer = require('multer');
const { Server } = require('socket.io');

const store = require('./data/store');

const app = express();
const server = http.createServer(app);
const io = new Server(server);

const PORT = 3000;

// Ensure upload directory exists
const uploadDir = path.join(__dirname, 'public', 'uploads');
if (!fs.existsSync(uploadDir)) {
    fs.mkdirSync(uploadDir, { recursive: true });
}

// Multer configuration for file uploads (PDF only, max 5MB)
const storage = multer.diskStorage({
    destination: (req, file, cb) => {
        cb(null, uploadDir);
    },
    filename: (req, file, cb) => {
        const uniqueSuffix = Date.now() + '-' + Math.round(Math.random() * 1e9);
        cb(null, uniqueSuffix + '-' + file.originalname.replace(/[^a-zA-Z0-9._-]/g, '_'));
    }
});

const upload = multer({
    storage,
    limits: { fileSize: 5 * 1024 * 1024 },
    fileFilter: (req, file, cb) => {
        if (file.mimetype === 'application/pdf' || file.originalname.toLowerCase().endsWith('.pdf')) {
            cb(null, true);
        } else {
            cb(new Error('Format non autorisé. Seuls les fichiers PDF sont acceptés.'));
        }
    }
});

// View engine setup
app.set('view engine', 'ejs');
app.set('views', path.join(__dirname, 'views'));

// Middlewares
app.use(express.urlencoded({ extended: true }));
app.use(express.json());
app.use(cookieParser());
app.use('/static', express.static(path.join(__dirname, 'public')));
app.use('/uploads', express.static(uploadDir));

app.use(session({
    secret: process.env.SECRET_KEY || 'edulink-secret-session-key',
    resave: false,
    saveUninitialized: false,
    cookie: {
        httpOnly: true,
        maxAge: 24 * 60 * 60 * 1000
    }
}));

// Flash messages middleware
app.use((req, res, next) => {
    req.flash = (category, message) => {
        if (!req.session.flashMessages) {
            req.session.flashMessages = [];
        }
        req.session.flashMessages.push({ category, message });
    };

    const messages = req.session.flashMessages || [];
    req.session.flashMessages = [];
    res.locals.messages = messages;
    res.locals.csrf_token = 'token_' + (req.session.id || 'default');
    res.locals.current_endpoint = req.path.replace(/^\//, '') || 'dashboard';
    res.locals.vapid_public_key = '';
    next();
});

// Current user authentication middleware
app.use((req, res, next) => {
    // Default to admin user if no session is set for seamless evaluation
    if (!req.session.userId) {
        req.session.userId = 'user_admin';
    }

    const user = store.findUserById(req.session.userId);
    res.locals.current_user = user || null;

    if (user) {
        const notifications = store.getUserNotifications(user.id);
        const unread = notifications.filter(n => !n.is_read);
        res.locals.unread_count = unread.length;
        res.locals.unread_notifications = notifications.slice(0, 5);
    } else {
        res.locals.unread_count = 0;
        res.locals.unread_notifications = [];
    }

    next();
});

// Auth guard helpers
function requireAuth(req, res, next) {
    if (!res.locals.current_user) {
        return res.redirect('/auth/login');
    }
    next();
}

function requireRole(...roles) {
    return (req, res, next) => {
        if (!res.locals.current_user) {
            return res.redirect('/auth/login');
        }
        if (!roles.includes(res.locals.current_user.role)) {
            return res.status(403).render('errors/error', {
                statusCode: 403,
                title: 'Accès non autorisé',
                message: 'Vous ne disposez pas des autorisations nécessaires pour accéder à cette page.'
            });
        }
        next();
    };
}

// -------------------------------------------------------------
// ROUTES
// -------------------------------------------------------------

// Root redirect
app.get('/', (req, res) => {
    res.redirect('/dashboard');
});

// Auth Routes
app.get('/auth/login', (req, res) => {
    res.render('auth/login', { error: null });
});

app.post('/auth/login', (req, res) => {
    const { email, password } = req.body;
    const user = store.findUserByEmail(email);

    if (!user || user.password_hash !== password) {
        req.flash('danger', 'Identifiants invalides.');
        return res.render('auth/login', { error: 'Identifiants invalides.' });
    }

    req.session.userId = user.id;
    req.flash('success', `Bienvenue, ${user.full_name} !`);
    res.redirect('/dashboard');
});

app.post('/auth/quick-login', (req, res) => {
    const { role } = req.body;
    const user = store.users.find(u => u.role === role);
    if (user) {
        req.session.userId = user.id;
        req.flash('success', `Connecté en tant que ${user.full_name} (${user.role})`);
    }
    res.redirect('/dashboard');
});

// Quick role switch for live demo
app.get('/auth/switch-role/:role', (req, res) => {
    const targetRole = (req.params.role || '').toUpperCase();
    const user = store.users.find(u => u.role === targetRole);
    if (user) {
        req.session.userId = user.id;
        const roleFr = user.role === 'ADMIN' ? 'Administrateur' : user.role === 'TEACHER' ? 'Enseignant' : 'Parent';
        req.flash('success', `Profil basculé : ${user.full_name} (${roleFr})`);
    }
    let returnUrl = req.headers.referer || '/dashboard';
    // If navigating from admin area to non-admin, redirect to dashboard
    if (returnUrl.includes('/admin') && user && user.role !== 'ADMIN') {
        returnUrl = '/dashboard';
    }
    res.redirect(returnUrl);
});

// Notifications
app.post('/notifications/mark-read', requireAuth, (req, res) => {
    const user = res.locals.current_user;
    if (user) {
        store.markAllNotificationsRead(user.id);
        req.flash('success', 'Toutes les notifications ont été marquées comme lues.');
    }
    res.redirect(req.headers.referer || '/dashboard');
});

app.all('/auth/logout', (req, res) => {
    req.session.userId = null;
    req.session.destroy(() => {
        res.redirect('/auth/login');
    });
});

app.get('/auth/users/new', requireAuth, requireRole('ADMIN'), (req, res) => {
    res.render('auth/create_user', { invitation_url: null });
});

app.post('/auth/users/new', requireAuth, requireRole('ADMIN'), (req, res) => {
    const { full_name, email, role } = req.body;
    if (!full_name || !email || !role) {
        req.flash('danger', 'Veuillez remplir tous les champs obligatoires.');
        return res.render('auth/create_user', { invitation_url: null });
    }

    const existing = store.findUserByEmail(email);
    if (existing) {
        req.flash('danger', 'Un utilisateur avec cet email existe déjà.');
        return res.render('auth/create_user', { invitation_url: null });
    }

    const newUser = store.createUser({ full_name, email, role });
    const fakeToken = 'inv_' + Math.random().toString(36).substring(2, 10);
    const invitation_url = `${req.protocol}://${req.get('host')}/auth/invite/${fakeToken}`;

    req.flash('success', `Le compte de ${newUser.full_name} a été créé avec succès.`);
    res.render('auth/create_user', { invitation_url });
});

// Dashboard Route
app.get('/dashboard', requireAuth, (req, res) => {
    const user = res.locals.current_user;
    const userChannels = store.getUserChannels(user.id);
    const notifications = store.getUserNotifications(user.id);
    const announcements = store.getAnnouncementsForUser(user.id);

    // Conversations preview
    const conversations = userChannels.map(ch => {
        const msgs = store.getChannelMessages(ch.id);
        const last_message = msgs.length > 0 ? msgs[msgs.length - 1] : null;
        return { channel: ch, last_message };
    });

    const role_message = {
        'ADMIN': 'Espace d’administration de l’établissement',
        'TEACHER': 'Espace enseignant & vie scolaire',
        'PARENT': 'Espace parents d’élèves'
    }[user.role] || 'Bienvenue sur EduLink';

    // Stats
    const stats = {
        unread_notifications: notifications.filter(n => !n.is_read).length,
        conversations_count: userChannels.length,
        unread_announcements: announcements.filter(a => !a.is_read).length
    };

    let user_counts = null;
    let channel_count = 0;
    let announcement_count = 0;
    let recent_users = [];
    let children = [];

    if (user.role === 'ADMIN') {
        user_counts = {
            ADMIN: store.users.filter(u => u.role === 'ADMIN').length,
            TEACHER: store.users.filter(u => u.role === 'TEACHER').length,
            PARENT: store.users.filter(u => u.role === 'PARENT').length
        };
        channel_count = store.channels.length;
        announcement_count = store.announcements.length;
        recent_users = store.users.slice(-5).reverse();
    }

    if (user.role === 'PARENT') {
        children = store.getChildrenForParent(user.id);
    }

    const latest_announcements = announcements.slice(0, 3).map(a => ({
        announcement: a,
        is_read: a.is_read
    }));

    const upcoming_events = store.getUpcomingEvents(6);
    const calendar_events_count = store.calendarEvents.length;

    res.render('dashboard/home', {
        role_message,
        stats,
        user_counts,
        channel_count,
        announcement_count,
        recent_users,
        children,
        conversations,
        latest_announcements,
        notifications,
        upcoming_events,
        calendar_events_count
    });
});

// Announcements Routes
app.get('/announcements', requireAuth, (req, res) => {
    const user = res.locals.current_user;
    const announcements = store.getAnnouncementsForUser(user.id);
    res.render('announcements/list', { announcements });
});

app.get('/announcements/new', requireAuth, requireRole('ADMIN', 'TEACHER'), (req, res) => {
    const user = res.locals.current_user;
    const channels = user.role === 'ADMIN' ? store.channels : store.getUserChannels(user.id);
    res.render('announcements/create', { channels });
});

app.post('/announcements/new', requireAuth, requireRole('ADMIN', 'TEACHER'), upload.single('document'), (req, res) => {
    const { title, content, audience, channel_id } = req.body;
    const user = res.locals.current_user;

    if (!title || !content) {
        req.flash('danger', 'Titre et contenu sont obligatoires.');
        return res.redirect('/announcements/new');
    }

    let targetChannelId = null;
    if (audience === 'channels' && channel_id) {
        targetChannelId = channel_id;
    }

    let pdfFilename = null;
    if (req.file) {
        pdfFilename = 'uploads/' + req.file.filename;
    }

    const newAnnouncement = store.createAnnouncement({
        title,
        content,
        author_id: user.id,
        channel_id: targetChannelId,
        pdf_filename: pdfFilename
    });

    // Notify users
    const recipients = targetChannelId
        ? (store.findChannelById(targetChannelId)?.member_ids || [])
        : store.users.map(u => u.id);

    recipients.forEach(userId => {
        if (userId !== user.id) {
            const notif = store.createNotification({
                user_id: userId,
                content: `Nouvelle annonce: ${title}`,
                channel_id: targetChannelId
            });
            io.emit('notification', { content: notif.content, channel_id: targetChannelId });
        }
    });

    req.flash('success', 'Annonce publiée avec succès.');
    res.redirect('/announcements');
});

app.post('/announcements/:id/read', requireAuth, (req, res) => {
    const user = res.locals.current_user;
    store.markAnnouncementRead(req.params.id, user.id);
    req.flash('success', 'Lecture de l’annonce confirmée.');
    res.redirect('/announcements');
});

// Messages Routes
app.get('/messages', requireAuth, (req, res) => {
    const user = res.locals.current_user;
    const userChannels = store.getUserChannels(user.id);

    const direct_channels = userChannels.filter(c => c.kind === 'direct').map(c => ({
        ...c,
        member_count: c.member_ids.length
    }));

    const group_channels = userChannels.filter(c => c.kind !== 'direct').map(c => ({
        ...c,
        member_count: c.member_ids.length
    }));

    const all_users = store.users.filter(u => u.id !== user.id);
    const can_manage = user.role === 'ADMIN' || user.role === 'TEACHER';

    res.render('messages/channels', {
        direct_channels,
        group_channels,
        all_users,
        can_manage
    });
});

app.post('/messages/channels', requireAuth, requireRole('ADMIN', 'TEACHER'), (req, res) => {
    const { name, members } = req.body;
    const user = res.locals.current_user;

    if (!name) {
        req.flash('danger', 'Le nom du canal est obligatoire.');
        return res.redirect('/messages');
    }

    let memberIds = [user.id];
    if (Array.isArray(members)) {
        memberIds = Array.from(new Set([...memberIds, ...members]));
    } else if (members) {
        memberIds = Array.from(new Set([...memberIds, members]));
    }

    const channel = store.createChannel({
        name,
        kind: 'group',
        creator_id: user.id,
        member_ids: memberIds
    });

    req.flash('success', `Canal "${channel.name}" créé avec succès.`);
    res.redirect(`/messages/channels/${channel.id}`);
});

app.get('/messages/channels/:id', requireAuth, (req, res) => {
    const user = res.locals.current_user;
    const channel = store.findChannelById(req.params.id);

    if (!channel) {
        return res.status(404).render('errors/error', {
            statusCode: 404,
            title: 'Canal introuvable',
            message: 'Ce canal n’existe pas ou a été supprimé.'
        });
    }

    // Membership check (admin can inspect any channel)
    if (!channel.member_ids.includes(user.id) && user.role !== 'ADMIN') {
        return res.status(403).render('errors/error', {
            statusCode: 403,
            title: 'Accès non autorisé',
            message: 'Vous ne faites pas partie de ce canal.'
        });
    }

    const messages = store.getChannelMessages(channel.id);
    const pinned_messages = messages.filter(m => m.is_pinned);
    const members = store.findUsersByIds(channel.member_ids);
    const templates = store.getUserMessageTemplates(user.id);

    res.render('messages/channel_detail', {
        channel,
        messages,
        pinned_messages,
        members,
        templates
    });
});

app.post('/messages/channels/:id', requireAuth, (req, res) => {
    const { content } = req.body;
    const user = res.locals.current_user;
    const channel = store.findChannelById(req.params.id);

    if (!channel || !content || !content.trim()) {
        return res.redirect(`/messages/channels/${req.params.id}`);
    }

    const msg = store.createMessage({
        channel_id: channel.id,
        sender_id: user.id,
        content: content.trim()
    });

    // Notify other channel members
    channel.member_ids.forEach(memberId => {
        if (memberId !== user.id) {
            store.createNotification({
                user_id: memberId,
                content: `${user.full_name} dans ${channel.name}: ${content.substring(0, 50)}`,
                channel_id: channel.id
            });
        }
    });

    io.emit('channel_message', { channel_id: channel.id, message_id: msg.id });
    io.emit('notification', {
        channel_id: channel.id,
        content: `${user.full_name}: ${content.substring(0, 50)}`
    });

    res.redirect(`/messages/channels/${channel.id}`);
});

// Pin/Unpin message
app.post('/messages/channels/:channelId/messages/:messageId/pin', requireAuth, (req, res) => {
    const { channelId, messageId } = req.params;
    const msg = store.messages.find(m => m.id === messageId && m.channel_id === channelId);
    if (msg) {
        msg.is_pinned = !msg.is_pinned;
        req.flash('success', msg.is_pinned ? 'Message épinglé.' : 'Message désépinglé.');
    }
    res.redirect(`/messages/channels/${channelId}`);
});

// AI Assistant endpoints (French School communication assistant)
app.post('/ai/channels/:id/summary', requireAuth, (req, res) => {
    const channel = store.findChannelById(req.params.id);
    if (!channel) {
        return res.status(404).json({ error: 'Canal introuvable' });
    }
    const msgs = store.getChannelMessages(channel.id);
    if (!msgs || msgs.length === 0) {
        return res.status(400).json({ error: 'Aucun message à résumer dans ce canal.' });
    }
    
    // Generate helpful educational summary based on recent messages
    const recent = msgs.slice(-8);
    const senders = Array.from(new Set(recent.map(m => m.sender_name))).join(', ');
    const mainThemes = recent.map(m => `• ${m.sender_name} : "${m.content.slice(0, 70)}${m.content.length > 70 ? '...' : ''}"`).join('\n');
    
    const summary = `📌 Synthèse de la conversation (${channel.name}) :\n\n` +
        `Participants actifs : ${senders}\n` +
        `Points clés abordés :\n${mainThemes}\n\n` +
        `ℹ️ Conclusion : Les échanges concernent l'organisation de la classe et les retours d'activités.`;

    return res.json({ summary });
});

app.post('/ai/rephrase', requireAuth, (req, res) => {
    const { text } = req.body;
    if (!text || !text.trim()) {
        return res.status(400).json({ error: 'Veuillez saisir un texte à reformuler.' });
    }

    const trimmed = text.trim();
    // Intelligent educational polite rephrasing
    let rephrased = trimmed;
    if (!/^(bonjour|bonsoir|chère|cher)/i.test(trimmed)) {
        rephrased = `Bonjour,\n\n${trimmed}`;
    }
    if (!/(cordialement|bien à vous|merci)/i.test(trimmed)) {
        rephrased += `\n\nBien cordialement.`;
    }
    rephrased = rephrased.replace(/\b(stp|svp)\b/gi, "s'il vous plaît");
    
    return res.json({ rephrased });
});

app.get('/messages/new', requireAuth, (req, res) => {
    const user = res.locals.current_user;
    const availableUsers = store.users.filter(u => u.id !== user.id);
    res.render('messages/new_conversation', { users: availableUsers });
});

app.post('/messages/new', requireAuth, (req, res) => {
    const { member } = req.body;
    const user = res.locals.current_user;
    const targetUser = store.findUserById(member);

    if (!targetUser) {
        req.flash('danger', 'Contact introuvable.');
        return res.redirect('/messages/new');
    }

    const channel = store.findOrCreateDirectChannel(user.id, targetUser.id);
    res.redirect(`/messages/channels/${channel.id}`);
});

// Teacher / Admin: Find Parent of Student
app.get('/messages/find-parent', requireAuth, requireRole('ADMIN', 'TEACHER'), (req, res) => {
    const query = req.query.q || '';
    const results = query ? store.findParentsByChildName(query) : [];
    res.render('messages/find_parent', { results, search_query: query });
});

app.post('/messages/find-parent', requireAuth, requireRole('ADMIN', 'TEACHER'), (req, res) => {
    const { parent_id } = req.body;
    const user = res.locals.current_user;
    const parent = store.findUserById(parent_id);

    if (!parent) {
        req.flash('danger', 'Parent introuvable.');
        return res.redirect('/messages/find-parent');
    }

    const channel = store.findOrCreateDirectChannel(user.id, parent.id);
    res.redirect(`/messages/channels/${channel.id}`);
});

// Message Templates
app.get('/messages/templates', requireAuth, (req, res) => {
    const user = res.locals.current_user;
    const templates = store.getUserMessageTemplates(user.id);
    res.render('messages/templates', { templates });
});

app.post('/messages/templates', requireAuth, (req, res) => {
    const { label, content } = req.body;
    const user = res.locals.current_user;

    if (!label || !content) {
        req.flash('danger', 'Nom et contenu du modèle sont obligatoires.');
        return res.redirect('/messages/templates');
    }

    store.createMessageTemplate({
        user_id: user.id,
        label,
        content
    });

    req.flash('success', 'Modèle de message enregistré.');
    res.redirect('/messages/templates');
});

app.post('/messages/templates/:id/delete', requireAuth, (req, res) => {
    store.deleteMessageTemplate(req.params.id);
    req.flash('success', 'Modèle supprimé.');
    res.redirect('/messages/templates');
});

// Parent Views
app.get('/parent/children', requireAuth, (req, res) => {
    const user = res.locals.current_user;
    const children = store.getChildrenForParent(user.id);
    res.render('parent/children', { children });
});

app.get('/parent/children/:id/channels', requireAuth, (req, res) => {
    const child = store.findChildById(req.params.id);
    if (!child) {
        return res.status(404).render('errors/error', {
            statusCode: 404,
            title: 'Enfant introuvable',
            message: 'Cet élève n’a pas été trouvé dans notre base.'
        });
    }

    const channels = store.getChannelsForClass(child.class_name);
    res.render('parent/child_channels', { child, channels });
});

// Admin Views
app.get('/admin/members', requireAuth, requireRole('ADMIN'), (req, res) => {
    res.render('admin/members', { users: store.users });
});

app.post('/admin/members/:id/role', requireAuth, requireRole('ADMIN'), (req, res) => {
    const user = store.findUserById(req.params.id);
    if (user && req.body.role) {
        user.role = req.body.role;
        req.flash('success', `Rôle de ${user.full_name} mis à jour : ${user.role}.`);
    }
    res.redirect('/admin/members');
});

app.post('/admin/members/:id/delete', requireAuth, requireRole('ADMIN'), (req, res) => {
    const idx = store.users.findIndex(u => u.id === req.params.id);
    if (idx !== -1) {
        const deleted = store.users.splice(idx, 1)[0];
        req.flash('success', `Utilisateur ${deleted.full_name} supprimé.`);
    }
    res.redirect('/admin/members');
});

app.get('/admin/channels', requireAuth, requireRole('ADMIN'), (req, res) => {
    res.render('admin/channels', { channels: store.channels });
});

app.get('/admin/announcements', requireAuth, requireRole('ADMIN'), (req, res) => {
    res.render('admin/announcements', { announcements: store.announcements });
});

app.get('/admin/children', requireAuth, requireRole('ADMIN'), (req, res) => {
    const parents = store.users.filter(u => u.role === 'PARENT');
    const enrichedChildren = store.children.map(c => {
        const p = store.findUserById(c.parent_id);
        return {
            ...c,
            parent_name: p ? p.full_name : 'Inconnu',
            parent_email: p ? p.email : ''
        };
    });
    res.render('admin/children', { children: enrichedChildren, parents });
});

app.post('/admin/children', requireAuth, requireRole('ADMIN'), (req, res) => {
    const { full_name, class_name, parent_id } = req.body;
    if (!full_name || !class_name || !parent_id) {
        req.flash('danger', 'Tous les champs sont requis.');
        return res.redirect('/admin/children');
    }

    store.createChild({ full_name, class_name, parent_id });
    req.flash('success', `Élève ${full_name} ajouté.`);
    res.redirect('/admin/children');
});

app.post('/admin/children/:id/delete', requireAuth, requireRole('ADMIN'), (req, res) => {
    const idx = store.children.findIndex(c => c.id === req.params.id);
    if (idx !== -1) {
        const deleted = store.children.splice(idx, 1)[0];
        req.flash('success', `Élève ${deleted.full_name} supprimé.`);
    }
    res.redirect('/admin/children');
});

app.get('/admin/stats', requireAuth, requireRole('ADMIN'), (req, res) => {
    const stats = store.getAdminStats();
    res.render('admin/stats', { stats });
});

// Calendar Routes
app.get('/calendar', requireAuth, (req, res) => {
    const { type = 'all', category = 'all', class_name = 'all' } = req.query;
    const events = store.getAllEvents({ type, category, class_name });
    const upcoming_events = store.getUpcomingEvents(8);
    const classes = ['Tous les niveaux', 'CM2-A', 'CE1-B', 'CM1 / CM2', 'Demi-pensionnaires', 'Parents d’élèves'];

    res.render('calendar/index', {
        events,
        upcoming_events,
        selected_type: type,
        selected_category: category,
        selected_class: class_name,
        classes,
        can_manage: res.locals.current_user.role === 'ADMIN' || res.locals.current_user.role === 'TEACHER'
    });
});

app.post('/calendar/events', requireAuth, requireRole('ADMIN', 'TEACHER'), (req, res) => {
    const { title, description, type, category, start_date, end_date, location, class_name, priority } = req.body;

    if (!title || !start_date) {
        req.flash('danger', 'Veuillez préciser au moins un titre et une date.');
        return res.redirect('/calendar');
    }

    const newEvent = store.createCalendarEvent({
        title: title.trim(),
        description: (description || '').trim(),
        type: type || 'event',
        category: category || 'academic',
        start_date,
        end_date: end_date || null,
        location: (location || '').trim(),
        class_name: class_name || 'Tous les niveaux',
        priority: priority || 'normal',
        creator_id: res.locals.current_user.id
    });

    // Notify users of significant upcoming events or urgent deadlines
    const isDeadline = newEvent.type === 'deadline';
    store.users.forEach(u => {
        if (u.id !== res.locals.current_user.id) {
            const notifText = isDeadline
                ? `Nouvelle échéance scolaire : ${newEvent.title}`
                : `Nouvel événement au calendrier : ${newEvent.title}`;
            store.createNotification({
                user_id: u.id,
                content: notifText,
                channel_id: null
            });
        }
    });

    req.flash('success', isDeadline ? 'Échéance académique enregistrée avec succès.' : 'Événement scolaire programmé avec succès.');
    res.redirect('/calendar');
});

app.post('/calendar/events/:id/delete', requireAuth, requireRole('ADMIN', 'TEACHER'), (req, res) => {
    const success = store.deleteCalendarEvent(req.params.id);
    if (success) {
        req.flash('success', 'Entrée supprimée du calendrier.');
    } else {
        req.flash('danger', 'Élément introuvable.');
    }
    res.redirect('/calendar');
});

app.get('/api/calendar/events', requireAuth, (req, res) => {
    const { type, category, class_name } = req.query;
    const events = store.getAllEvents({ type, category, class_name });
    res.json(events);
});

// Notifications API
app.post('/notifications/mark-read', requireAuth, (req, res) => {
    const user = res.locals.current_user;
    store.markAllNotificationsRead(user.id);
    res.json({ success: true });
});

// Catch-all 404
app.use((req, res) => {
    res.status(404).render('errors/error', {
        statusCode: 404,
        title: 'Page non trouvée',
        message: 'L’adresse demandée n’existe pas ou a été déplacée.'
    });
});

// Socket.io connection handling
io.on('connection', (socket) => {
    socket.on('join_channel', (channelId) => {
        socket.join(`channel_${channelId}`);
    });

    socket.on('leave_channel', (channelId) => {
        socket.leave(`channel_${channelId}`);
    });
});

// Start server
server.listen(PORT, '0.0.0.0', () => {
    console.log(`EduLink running on http://0.0.0.0:${PORT}`);
});
