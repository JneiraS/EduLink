// In-memory data store for EduLink (Node.js runtime)

const users = [
  {
    id: '1',
    full_name: 'Admin EduLink',
    email: 'admin@edulink.local',
    password: 'admin123',
    password_hash: 'admin123',
    role: 'ADMIN',
    created_at: new Date('2026-09-01T08:00:00Z'),
  },
  {
    id: '2',
    full_name: 'Claire Dupont',
    email: 'claire.dupont@edulink.local',
    password: 'teacher123',
    password_hash: 'teacher123',
    role: 'TEACHER',
    created_at: new Date('2026-09-02T09:00:00Z'),
  },
  {
    id: '3',
    full_name: 'Thomas Bernard',
    email: 'thomas.bernard@edulink.local',
    password: 'teacher123',
    password_hash: 'teacher123',
    role: 'TEACHER',
    created_at: new Date('2026-09-02T10:00:00Z'),
  },
  {
    id: '4',
    full_name: 'Marc Martin',
    email: 'marc.martin@edulink.local',
    password: 'parent123',
    password_hash: 'parent123',
    role: 'PARENT',
    created_at: new Date('2026-09-03T11:00:00Z'),
  },
  {
    id: '5',
    full_name: 'Sophie Lefebvre',
    email: 'sophie.lefebvre@edulink.local',
    password: 'parent123',
    password_hash: 'parent123',
    role: 'PARENT',
    created_at: new Date('2026-09-03T14:00:00Z'),
  },
];

const children = [
  {
    id: '1',
    full_name: 'Lucas Martin',
    class_name: 'CM2-A',
    parent_id: '4',
    created_at: new Date('2026-09-03T11:30:00Z'),
  },
  {
    id: '2',
    full_name: 'Emma Martin',
    class_name: 'CE1-B',
    parent_id: '4',
    created_at: new Date('2026-09-03T11:35:00Z'),
  },
  {
    id: '3',
    full_name: 'Hugo Lefebvre',
    class_name: 'CM2-A',
    parent_id: '5',
    created_at: new Date('2026-09-03T14:30:00Z'),
  },
];

const channels = [
  {
    id: '1',
    name: 'Classe de CM2-A',
    kind: 'group',
    creator_id: '2',
    member_ids: ['1', '2', '4', '5'],
    created_at: new Date('2026-09-02T09:30:00Z'),
  },
  {
    id: '2',
    name: 'Classe de CE1-B',
    kind: 'group',
    creator_id: '3',
    member_ids: ['1', '3', '4'],
    created_at: new Date('2026-09-02T10:30:00Z'),
  },
  {
    id: '3',
    name: 'Vie Scolaire & Périscolaire',
    kind: 'group',
    creator_id: '1',
    member_ids: ['1', '2', '3', '4', '5'],
    created_at: new Date('2026-09-01T08:30:00Z'),
  },
  {
    id: '4',
    name: 'Claire Dupont & Marc Martin',
    kind: 'direct',
    creator_id: '2',
    member_ids: ['2', '4'],
    created_at: new Date('2026-09-04T10:00:00Z'),
  },
];

const messages = [
  {
    id: '1',
    channel_id: '1',
    sender_id: '2',
    content: 'Bienvenue à tous les parents dans l’espace d’échange de la classe CM2-A !',
    is_pinned: true,
    created_at: new Date(Date.now() - 3 * 86400000),
  },
  {
    id: '2',
    channel_id: '1',
    sender_id: '4',
    content: 'Merci Mme Dupont. Pouvons-nous avoir la liste des fournitures complémentaires ?',
    is_pinned: false,
    created_at: new Date(Date.now() - 2 * 86400000),
  },
  {
    id: '3',
    channel_id: '1',
    sender_id: '2',
    content: 'Bonjour M. Martin, la liste a été déposée dans l’onglet Annonces avec le PDF officiel.',
    is_pinned: false,
    created_at: new Date(Date.now() - 1 * 86400000),
  },
  {
    id: '4',
    channel_id: '4',
    sender_id: '2',
    content: 'Bonjour M. Martin, un point rapide concernant les progrès de Lucas en mathématiques.',
    is_pinned: false,
    created_at: new Date(Date.now() - 12 * 3600000),
  },
  {
    id: '5',
    channel_id: '4',
    sender_id: '4',
    content: 'Bonjour Mme Dupont, avec plaisir. Êtes-vous disponible mardi après 16h30 ?',
    is_pinned: false,
    created_at: new Date(Date.now() - 2 * 3600000),
  },
];

const announcements = [
  {
    id: '1',
    title: 'Règlement intérieur et protocole sanitaire 2026-2027',
    content: 'Veuillez prendre connaissance du règlement intérieur de l’école pour l’année scolaire en cours.',
    author_id: '1',
    channel_id: null,
    pdf_filename: null,
    created_at: new Date(Date.now() - 5 * 86400000),
  },
  {
    id: '2',
    title: 'Sortie pédagogique au Musée des Sciences',
    content: 'La classe de CM2-A effectuera une sortie le vendredi 26 septembre. Pique-nique à prévoir.',
    author_id: '2',
    channel_id: '1',
    pdf_filename: null,
    created_at: new Date(Date.now() - 2 * 86400000),
  },
  {
    id: '3',
    title: 'Élection des représentants des parents d’élèves',
    content: 'Le scrutin aura lieu le 10 octobre. Les déclarations de candidature sont ouvertes.',
    author_id: '1',
    channel_id: null,
    pdf_filename: null,
    created_at: new Date(Date.now() - 1 * 86400000),
  },
];

const announcementReads = new Map([
  ['1_1', true],
  ['1_4', true],
  ['2_4', false],
  ['3_4', false],
]);

const notifications = [
  {
    id: '1',
    user_id: '4',
    channel_id: '1',
    content: 'Nouveau message de Claire Dupont dans Classe de CM2-A',
    is_read: false,
    created_at: new Date(Date.now() - 2 * 3600000),
  },
  {
    id: '2',
    user_id: '4',
    channel_id: '4',
    content: 'Nouveau message de Claire Dupont dans conversation privée',
    is_read: false,
    created_at: new Date(Date.now() - 12 * 3600000),
  },
  {
    id: '3',
    user_id: '4',
    channel_id: null,
    content: 'Nouvelle annonce : Sortie pédagogique au Musée des Sciences',
    is_read: true,
    created_at: new Date(Date.now() - 24 * 3600000),
  },
  {
    id: '4',
    user_id: '1',
    channel_id: null,
    content: 'Bienvenue sur EduLink en tant qu’administrateur',
    is_read: false,
    created_at: new Date(Date.now() - 1 * 3600000),
  }
];

const messageTemplates = [
  {
    id: '1',
    user_id: '2',
    label: 'Rappel réunion',
    content: 'Bonjour, je vous rappelle la réunion prévue ce soir à l’école. Merci de votre présence.',
  },
  {
    id: '2',
    user_id: '2',
    label: 'Prise en compte absence',
    content: 'Bonjour, j’ai bien reçu l’information concernant l’absence de votre enfant. Merci pour votre diligence.',
  },
  {
    id: '3',
    user_id: '1',
    label: 'Message administratif',
    content: 'Bonjour, merci de bien vouloir compléter les fiches d’urgence distribuées aux élèves.',
  }
];

// Helper methods
function findUserById(id) {
  if (id === 'user_admin') id = '1';
  return users.find((u) => u.id === String(id)) || null;
}

function findUserByEmail(email) {
  return users.find((u) => u.email.toLowerCase() === String(email).trim().toLowerCase()) || null;
}

function findUsersByIds(ids) {
  const set = new Set((ids || []).map(String));
  return users.filter((u) => set.has(String(u.id)));
}

function createUser({ full_name, email, role }) {
  const newUser = {
    id: String(Date.now()),
    full_name,
    email,
    password: 'password123',
    password_hash: 'password123',
    role,
    created_at: new Date(),
  };
  users.push(newUser);
  return newUser;
}

function getUserChannels(userId) {
  const uid = String(userId);
  return channels.filter((c) => c.member_ids.includes(uid));
}

function findChannelById(id) {
  return channels.find((c) => c.id === String(id)) || null;
}

function createChannel({ name, kind, creator_id, member_ids }) {
  const newChannel = {
    id: String(Date.now()),
    name,
    kind: kind || 'group',
    creator_id: String(creator_id),
    member_ids: (member_ids || []).map(String),
    created_at: new Date(),
  };
  channels.push(newChannel);
  return newChannel;
}

function findOrCreateDirectChannel(user1Id, user2Id) {
  const u1 = String(user1Id);
  const u2 = String(user2Id);
  let ch = channels.find(
    (c) => c.kind === 'direct' && c.member_ids.includes(u1) && c.member_ids.includes(u2)
  );

  if (!ch) {
    const user1 = findUserById(u1);
    const user2 = findUserById(u2);
    const name = `${user1?.full_name || 'Utilisateur'} & ${user2?.full_name || 'Utilisateur'}`;
    ch = createChannel({
      name,
      kind: 'direct',
      creator_id: u1,
      member_ids: [u1, u2],
    });
  }

  return ch;
}

function getChannelMessages(channelId) {
  return messages
    .filter((m) => m.channel_id === String(channelId))
    .map((m) => {
      const sender = findUserById(m.sender_id);
      return {
        ...m,
        sender_name: sender ? sender.full_name : 'Inconnu',
      };
    })
    .sort((a, b) => new Date(a.created_at) - new Date(b.created_at));
}

function createMessage({ channel_id, sender_id, content }) {
  const newMsg = {
    id: String(Date.now()),
    channel_id: String(channel_id),
    sender_id: String(sender_id),
    content,
    is_pinned: false,
    created_at: new Date(),
  };
  messages.push(newMsg);
  return newMsg;
}

function getAnnouncementsForUser(userId) {
  const uid = String(userId);
  const user = findUserById(uid);
  const userChannels = getUserChannels(uid).map((c) => c.id);

  return announcements
    .filter((a) => {
      if (!a.channel_id) return true; // Global announcement
      if (user && user.role === 'ADMIN') return true;
      return userChannels.includes(a.channel_id);
    })
    .map((a) => {
      const is_read = announcementReads.get(`${a.id}_${uid}`) || false;
      const ch = a.channel_id ? findChannelById(a.channel_id) : null;
      return {
        ...a,
        is_read,
        channel_name: ch ? ch.name : null,
      };
    })
    .sort((a, b) => new Date(b.created_at) - new Date(a.created_at));
}

function createAnnouncement({ title, content, author_id, channel_id, pdf_filename }) {
  const newA = {
    id: String(Date.now()),
    title,
    content,
    author_id: String(author_id),
    channel_id: channel_id ? String(channel_id) : null,
    pdf_filename: pdf_filename || null,
    created_at: new Date(),
  };
  announcements.push(newA);
  return newA;
}

function markAnnouncementRead(announcementId, userId) {
  announcementReads.set(`${announcementId}_${userId}`, true);
}

function getUserNotifications(userId) {
  const uid = String(userId);
  return notifications
    .filter((n) => n.user_id === uid)
    .sort((a, b) => new Date(b.created_at) - new Date(a.created_at));
}

function createNotification({ user_id, content, channel_id }) {
  const newN = {
    id: String(Date.now()),
    user_id: String(user_id),
    channel_id: channel_id ? String(channel_id) : null,
    content,
    is_read: false,
    created_at: new Date(),
  };
  notifications.push(newN);
  return newN;
}

function markAllNotificationsRead(userId) {
  const uid = String(userId);
  notifications.forEach((n) => {
    if (n.user_id === uid) {
      n.is_read = true;
    }
  });
}

function getChildrenForParent(parentId) {
  const pid = String(parentId);
  return children.filter((c) => c.parent_id === pid);
}

function findChildById(id) {
  return children.find((c) => c.id === String(id)) || null;
}

function createChild({ full_name, class_name, parent_id }) {
  const newC = {
    id: String(Date.now()),
    full_name,
    class_name,
    parent_id: String(parent_id),
    created_at: new Date(),
  };
  children.push(newC);
  return newC;
}

function findParentsByChildName(query) {
  const q = String(query).trim().toLowerCase();
  const matched = children.filter((c) => c.full_name.toLowerCase().includes(q));
  return matched.map((child) => {
    const parent = findUserById(child.parent_id);
    return {
      child,
      parent: parent || { id: child.parent_id, full_name: 'Parent inconnu', email: '' },
    };
  });
}

function getChannelsForClass(className) {
  return channels.filter((c) => c.name.toLowerCase().includes(className.toLowerCase()));
}

function getUserMessageTemplates(userId) {
  const uid = String(userId);
  return messageTemplates.filter((t) => t.user_id === uid);
}

function createMessageTemplate({ user_id, label, content }) {
  const newT = {
    id: String(Date.now()),
    user_id: String(user_id),
    label,
    content,
  };
  messageTemplates.push(newT);
  return newT;
}

function deleteMessageTemplate(id) {
  const idx = messageTemplates.findIndex((t) => t.id === String(id));
  if (idx !== -1) {
    messageTemplates.splice(idx, 1);
  }
}

function getAdminStats() {
  return {
    registrations_by_week: [
      { label: 'Sem 34', count: 1 },
      { label: 'Sem 35', count: 2 },
      { label: 'Sem 36', count: 2 },
      { label: 'Sem 37', count: 3 },
    ],
    users_by_role: {
      Administrateurs: users.filter((u) => u.role === 'ADMIN').length,
      Enseignants: users.filter((u) => u.role === 'TEACHER').length,
      Parents: users.filter((u) => u.role === 'PARENT').length,
    },
    messages_by_day: [
      { label: '01/09', count: 2 },
      { label: '03/09', count: 5 },
      { label: '05/09', count: 8 },
      { label: '08/09', count: 12 },
      { label: '10/09', count: 7 },
      { label: '12/09', count: 15 },
    ],
    top_channels: channels.map((c) => ({
      channel_name: c.name,
      count: messages.filter((m) => m.channel_id === c.id).length,
    })),
    announcement_read_rates: announcements.map((a) => ({
      title: a.title.slice(0, 20) + '...',
      read: 3,
      unread: 2,
    })),
    push_adoption: {
      subscribers: 4,
      total_users: users.length,
    },
  };
}

const calendarEvents = [
  {
    id: 'evt_1',
    title: 'Restitution des fiches d’urgence et d’assurance',
    description: 'Date limite impérative pour le retour des fiches d’urgence médicale et de l’attestation d’assurance scolaire signées.',
    type: 'deadline', // 'deadline' | 'event' | 'holiday'
    category: 'administrative', // 'administrative' | 'academic' | 'meeting' | 'outing' | 'holiday'
    start_date: new Date('2026-09-18T17:00:00'),
    end_date: null,
    location: 'Secrétariat / Cahier de liaison',
    class_name: 'Tous les niveaux',
    priority: 'urgent',
    creator_id: '1',
    created_at: new Date('2026-09-01T08:00:00Z'),
  },
  {
    id: 'evt_2',
    title: 'Réunion parents-professeurs : Classes de CM2 & CM1',
    description: 'Rencontre d’information de rentrée avec les enseignants pour présenter les programmes, sorties prévues et objectifs de l’année scolaire.',
    type: 'event',
    category: 'meeting',
    start_date: new Date('2026-09-15T18:00:00'),
    end_date: new Date('2026-09-15T20:00:00'),
    location: 'Salle polyvalente & Classes',
    class_name: 'CM1 / CM2',
    priority: 'high',
    creator_id: '2',
    created_at: new Date('2026-09-02T09:00:00Z'),
  },
  {
    id: 'evt_3',
    title: 'Séance photo de classe individuelle et groupe',
    description: 'Photographe officiel présent dans l’établissement. Tenue soignée souhaitée pour les enfants.',
    type: 'event',
    category: 'academic',
    start_date: new Date('2026-09-22T08:30:00'),
    end_date: new Date('2026-09-22T16:30:00'),
    location: 'Cour principale / Préau',
    class_name: 'Tous les niveaux',
    priority: 'normal',
    creator_id: '1',
    created_at: new Date('2026-09-03T10:00:00Z'),
  },
  {
    id: 'evt_4',
    title: 'Paiement forfait demi-pension (1er trimestre)',
    description: 'Date d’échéance pour le règlement de la restauration scolaire du 1er trimestre auprès de l’intendance ou en ligne.',
    type: 'deadline',
    category: 'administrative',
    start_date: new Date('2026-09-25T23:59:00'),
    end_date: null,
    location: 'Service intendance / Portail en ligne',
    class_name: 'Demi-pensionnaires',
    priority: 'high',
    creator_id: '1',
    created_at: new Date('2026-09-03T11:00:00Z'),
  },
  {
    id: 'evt_5',
    title: 'Journée nationale du sport scolaire (Cross solidaire)',
    description: 'Matinée d’activités sportives et parcours de cross pour toutes les classes au stade municipal.',
    type: 'event',
    category: 'outing',
    start_date: new Date('2026-09-30T09:00:00'),
    end_date: new Date('2026-09-30T12:00:00'),
    location: 'Stade municipal Jean Bouin',
    class_name: 'Tous les niveaux',
    priority: 'normal',
    creator_id: '2',
    created_at: new Date('2026-09-04T12:00:00Z'),
  },
  {
    id: 'evt_6',
    title: 'Dépôt des candidatures - Élections des représentants des parents',
    description: 'Clôture du dépôt des listes de candidats pour le conseil d’école auprès de la direction.',
    type: 'deadline',
    category: 'academic',
    start_date: new Date('2026-10-02T18:00:00'),
    end_date: null,
    location: 'Bureau de direction',
    class_name: 'Parents d’élèves',
    priority: 'urgent',
    creator_id: '1',
    created_at: new Date('2026-09-05T09:00:00Z'),
  },
  {
    id: 'evt_7',
    title: 'Élections des délégués et représentants des parents',
    description: 'Scrutin sur place (8h00 - 17h00) ou vote par correspondance via le carnet de liaison.',
    type: 'event',
    category: 'academic',
    start_date: new Date('2026-10-09T08:00:00'),
    end_date: new Date('2026-10-09T17:00:00'),
    location: 'Hall d’accueil de l’école',
    class_name: 'Tous les niveaux',
    priority: 'normal',
    creator_id: '1',
    created_at: new Date('2026-09-05T09:30:00Z'),
  },
  {
    id: 'evt_8',
    title: 'Sortie pédagogique : Musée d’Histoire Naturelle',
    description: 'Visite guidée dans le cadre du projet scientifique sur la biodiversité. Prévoir un pique-nique zéro déchet.',
    type: 'event',
    category: 'outing',
    start_date: new Date('2026-10-14T08:45:00'),
    end_date: new Date('2026-10-14T16:30:00'),
    location: 'Musée d’Histoire Naturelle',
    class_name: 'Classe de CM2-A',
    priority: 'normal',
    creator_id: '2',
    created_at: new Date('2026-09-06T14:00:00Z'),
  },
  {
    id: 'evt_9',
    title: 'Restitution des autorisations et fiches de sortie CM2',
    description: 'Dernier délai pour remettre les autorisations parentales signées pour la sortie au musée.',
    type: 'deadline',
    category: 'administrative',
    start_date: new Date('2026-10-09T16:30:00'),
    end_date: null,
    location: 'Enseignante CM2-A',
    class_name: 'Classe de CM2-A',
    priority: 'high',
    creator_id: '2',
    created_at: new Date('2026-09-06T14:30:00Z'),
  },
  {
    id: 'evt_10',
    title: 'Vacances de la Toussaint',
    description: 'Fin des cours le vendredi 16 octobre après la classe. Reprise des cours le lundi 2 novembre au matin.',
    type: 'holiday',
    category: 'holiday',
    start_date: new Date('2026-10-17T00:00:00'),
    end_date: new Date('2026-11-02T08:30:00'),
    location: 'Établissement fermé',
    class_name: 'Tous les niveaux',
    priority: 'normal',
    creator_id: '1',
    created_at: new Date('2026-09-01T08:00:00Z'),
  }
];

function getAllEvents(filters = {}) {
  let list = [...calendarEvents];

  if (filters.type && filters.type !== 'all') {
    list = list.filter(e => e.type === filters.type);
  }

  if (filters.category && filters.category !== 'all') {
    list = list.filter(e => e.category === filters.category);
  }

  if (filters.class_name && filters.class_name !== 'all') {
    list = list.filter(e => e.class_name === filters.class_name || e.class_name === 'Tous les niveaux');
  }

  // Sort by start_date ascending
  return list.sort((a, b) => new Date(a.start_date).getTime() - new Date(b.start_date).getTime());
}

function getUpcomingEvents(limit = 6) {
  // Return upcoming sorted from current perspective
  const sorted = [...calendarEvents].sort((a, b) => new Date(a.start_date).getTime() - new Date(b.start_date).getTime());
  return sorted.slice(0, limit);
}

function findEventById(id) {
  return calendarEvents.find(e => e.id === String(id)) || null;
}

function createCalendarEvent({
  title,
  description = '',
  type = 'event',
  category = 'academic',
  start_date,
  end_date = null,
  location = '',
  class_name = 'Tous les niveaux',
  priority = 'normal',
  creator_id = '1'
}) {
  const newEvent = {
    id: 'evt_' + Date.now(),
    title,
    description,
    type,
    category,
    start_date: new Date(start_date),
    end_date: end_date ? new Date(end_date) : null,
    location,
    class_name,
    priority,
    creator_id: String(creator_id),
    created_at: new Date()
  };
  calendarEvents.push(newEvent);
  return newEvent;
}

function deleteCalendarEvent(id) {
  const idx = calendarEvents.findIndex(e => e.id === String(id));
  if (idx !== -1) {
    calendarEvents.splice(idx, 1);
    return true;
  }
  return false;
}

module.exports = {
  users,
  children,
  channels,
  messages,
  announcements,
  announcementReads,
  notifications,
  messageTemplates,
  calendarEvents,
  findUserById,
  findUserByEmail,
  findUsersByIds,
  createUser,
  getUserChannels,
  findChannelById,
  createChannel,
  findOrCreateDirectChannel,
  getChannelMessages,
  createMessage,
  getAnnouncementsForUser,
  createAnnouncement,
  markAnnouncementRead,
  getUserNotifications,
  createNotification,
  markAllNotificationsRead,
  getChildrenForParent,
  findChildById,
  createChild,
  findParentsByChildName,
  getChannelsForClass,
  getUserMessageTemplates,
  createMessageTemplate,
  deleteMessageTemplate,
  getAdminStats,
  getAllEvents,
  getUpcomingEvents,
  findEventById,
  createCalendarEvent,
  deleteCalendarEvent,
};
