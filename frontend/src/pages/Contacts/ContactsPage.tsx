import React, { useEffect, useState } from 'react';
import api from '../../services/api';
import { motion, AnimatePresence } from 'framer-motion';
import {
  Users,
  Search,
  Star,
  Mail,
  Phone,
  Building,
  Briefcase,
  Globe,
  RefreshCw,
  Upload,
  UserPlus,
  Trash2
} from 'lucide-react';
import { Button } from '../../components/ui/Button';
import { Card } from '../../components/ui/Card';
import { Avatar } from '../../components/ui/Avatar';
import { Modal } from '../../components/ui/Modal';
import { Input } from '../../components/ui/Input';
import { Textarea } from '../../components/ui/Textarea';
import { useToastStore } from '../../store/useToastStore';
import { LoadingSpinner } from '../../components/ui/LoadingSpinner';
import { EmptyState } from '../../components/ui/EmptyState';

interface Contact {
  id: number;
  display_name: string;
  first_name?: string;
  last_name?: string;
  company?: string;
  job_title?: string;
  email: string;
  phone?: string;
  linkedin_url?: string;
  is_favorite: boolean;
  notes?: string;
}

export const ContactsPage: React.FC = () => {
  const [contacts, setContacts] = useState<Contact[]>([]);
  const [searchQuery, setSearchQuery] = useState('');
  const [loading, setLoading] = useState(false);
  const [syncing, setSyncing] = useState(false);
  const [isModalOpen, setIsModalOpen] = useState(false);
  const [isImportModalOpen, setIsImportModalOpen] = useState(false);
  const [csvContent, setCsvContent] = useState('');

  // Form states
  const [displayName, setDisplayName] = useState('');
  const [firstName, setFirstName] = useState('');
  const [lastName, setLastName] = useState('');
  const [email, setEmail] = useState('');
  const [phone, setPhone] = useState('');
  const [company, setCompany] = useState('');
  const [jobTitle, setJobTitle] = useState('');
  const [linkedinUrl, setLinkedinUrl] = useState('');
  const [notes, setNotes] = useState('');
  const [isFavorite, setIsFavorite] = useState(false);

  const { addToast } = useToastStore();

  const fetchContacts = async () => {
    setLoading(true);
    try {
      const response = await api.get('/contacts');
      setContacts(response.data);
    } catch (err) {
      console.error(err);
      addToast('error', 'Error Loading', 'Failed to retrieve your contacts from the database.');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchContacts();
  }, []);

  const handleSearch = async (val: string) => {
    setSearchQuery(val);
    if (!val.trim()) {
      fetchContacts();
      return;
    }
    try {
      const response = await api.post('/contacts/search', { query: val });
      setContacts(response.data);
    } catch (err) {
      console.error(err);
    }
  };

  const toggleFavorite = async (contact: Contact) => {
    try {
      const updated = { ...contact, is_favorite: !contact.is_favorite };
      await api.put(`/contacts/${contact.id}`, { is_favorite: !contact.is_favorite });
      setContacts(prev => prev.map(c => c.id === contact.id ? updated : c));
      addToast('success', 'Favorite Updated', `${contact.display_name} updated successfully.`);
    } catch (err) {
      console.error(err);
    }
  };

  const deleteContact = async (id: number) => {
    if (!window.confirm("Are you sure you want to delete this contact?")) return;
    try {
      await api.delete(`/contacts/${id}`);
      setContacts(prev => prev.filter(c => c.id !== id));
      addToast('success', 'Contact Deleted', 'Contact removed successfully.');
    } catch (err) {
      console.error(err);
      addToast('error', 'Delete Failed', 'Failed to delete contact.');
    }
  };

  const handleCreateContact = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!displayName.trim() || !email.trim()) return;

    try {
      const response = await api.post('/contacts', {
        display_name: displayName,
        first_name: firstName || undefined,
        last_name: lastName || undefined,
        email,
        phone: phone || undefined,
        company: company || undefined,
        job_title: jobTitle || undefined,
        linkedin_url: linkedinUrl || undefined,
        notes: notes || undefined,
        is_favorite: isFavorite
      });
      setContacts(prev => [response.data, ...prev]);
      setIsModalOpen(false);
      resetForm();
      addToast('success', 'Contact Created', `${displayName} was added successfully.`);
    } catch (err) {
      console.error(err);
      addToast('error', 'Creation Failed', 'Failed to create new contact.');
    }
  };

  const resetForm = () => {
    setDisplayName('');
    setFirstName('');
    setLastName('');
    setEmail('');
    setPhone('');
    setCompany('');
    setJobTitle('');
    setLinkedinUrl('');
    setNotes('');
    setIsFavorite(false);
  };

  const handleGoogleSync = async () => {
    setSyncing(true);
    try {
      addToast('info', 'Sync Started', 'Synchronizing contacts with Google People API...');
      const response = await api.post('/contacts/import', { provider: 'google' });
      setContacts(response.data);
      addToast('success', 'Sync Finished', 'Google Contacts successfully imported and merged.');
    } catch (err: any) {
      console.error(err);
      const detail = err.response?.data?.detail || '';
      if (detail.includes("Google token not found") || detail.includes("scope")) {
        addToast('error', 'Google Connection Required', 'Please connect your Google Account in Settings to authorize contacts.');
      } else {
        addToast('error', 'Sync Failed', 'Google Contacts synchronization failed.');
      }
    } finally {
      setSyncing(false);
    }
  };

  const handleCsvImport = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!csvContent.trim()) return;
    try {
      const response = await api.post('/contacts/import', { provider: 'csv', csv_content: csvContent });
      setContacts(response.data);
      setIsImportModalOpen(false);
      setCsvContent('');
      addToast('success', 'Import Completed', 'CSV file records imported and merged.');
    } catch (err) {
      console.error(err);
      addToast('error', 'Import Failed', 'Please verify CSV format and column headers.');
    }
  };

  return (
    <main className="flex-1 p-5 xl:p-6 overflow-y-auto min-h-0 flex flex-col gap-6">
      
      {/* Header Actions */}
      <div className="flex flex-col md:flex-row md:items-center justify-between gap-4">
        <div>
          <h1 className="text-xl font-bold text-slate-100 font-display flex items-center gap-2">
            <Users className="text-indigo-400" size={20} />
            Contact Intelligence
          </h1>
          <p className="text-xs text-zinc-400 mt-1">Manage network relationships. Schedule meetings using contact names.</p>
        </div>

        <div className="flex flex-wrap items-center gap-2">
          <Button variant="ghost" size="sm" onClick={handleGoogleSync} disabled={syncing} className="gap-2 border border-zinc-800">
            <RefreshCw size={14} className={syncing ? 'animate-spin' : ''} />
            Sync Google
          </Button>
          <Button variant="ghost" size="sm" onClick={() => setIsImportModalOpen(true)} className="gap-2 border border-zinc-800">
            <Upload size={14} />
            Import CSV
          </Button>
          <Button variant="primary" size="sm" onClick={() => setIsModalOpen(true)} className="gap-2">
            <UserPlus size={14} />
            Add Contact
          </Button>
        </div>
      </div>

      {/* Search Filter Bar */}
      <div className="relative w-full max-w-md text-left">
        <Search className="absolute left-3 top-1/2 -translate-y-1/2 text-zinc-500 w-4 h-4" />
        <input
          type="text"
          placeholder="Search contacts by name, email, company..."
          value={searchQuery}
          onChange={(e) => handleSearch(e.target.value)}
          className="w-full bg-zinc-900 border border-zinc-800 rounded-lg pl-10 pr-4 py-2 text-sm text-slate-100 placeholder-zinc-500 focus:outline-none focus:border-indigo-500"
        />
      </div>

      {/* Contacts Grid */}
      {loading ? (
        <div className="flex-1 flex items-center justify-center py-20">
          <LoadingSpinner size="lg" />
        </div>
      ) : contacts.length === 0 ? (
        <div className="flex-1 py-12">
          <EmptyState
            icon={Users}
            title="No Contacts"
            description="Create contacts or import them from CSV/Google to enable name-based intelligent meeting planning."
            actionLabel="Add new contact"
            onAction={() => setIsModalOpen(true)}
          />
        </div>
      ) : (
        <div className="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-3 gap-4">
          <AnimatePresence>
            {contacts.map((contact) => (
              <motion.div
                key={contact.id}
                initial={{ opacity: 0, scale: 0.95 }}
                animate={{ opacity: 1, scale: 1 }}
                exit={{ opacity: 0, scale: 0.95 }}
                transition={{ duration: 0.2 }}
              >
                <Card className="p-5 flex flex-col justify-between h-full group relative text-left">
                  {/* Top Header Card */}
                  <div className="flex items-start gap-4">
                    <Avatar name={contact.display_name} size="lg" />
                    
                    <div className="flex-1 overflow-hidden">
                      <div className="flex items-center gap-1.5">
                        <h3 className="font-display font-bold text-sm text-slate-200 truncate">{contact.display_name}</h3>
                        <button
                          onClick={() => toggleFavorite(contact)}
                          className="text-zinc-500 hover:text-amber-400 cursor-pointer"
                          title="Toggle favorite"
                        >
                          <Star size={14} fill={contact.is_favorite ? '#fbbf24' : 'none'} className={contact.is_favorite ? 'text-amber-400' : ''} />
                        </button>
                      </div>

                      {/* Job Info */}
                      {(contact.job_title || contact.company) && (
                        <p className="text-xs text-zinc-400 truncate mt-1 flex items-center gap-1.5">
                          {contact.company && <span className="flex items-center gap-1"><Building size={12} />{contact.company}</span>}
                          {contact.job_title && <span className="flex items-center gap-1"><Briefcase size={12} />{contact.job_title}</span>}
                        </p>
                      )}
                    </div>
                  </div>

                  {/* Body Info */}
                  <div className="mt-4 space-y-2 text-xs border-t border-zinc-900 pt-3">
                    <div className="flex items-center gap-2 text-zinc-400 truncate">
                      <Mail size={12} className="shrink-0" />
                      <span>{contact.email}</span>
                    </div>
                    {contact.phone && (
                      <div className="flex items-center gap-2 text-zinc-400 truncate">
                        <Phone size={12} className="shrink-0" />
                        <span>{contact.phone}</span>
                      </div>
                    )}
                    {contact.linkedin_url && (
                      <a
                        href={contact.linkedin_url}
                        target="_blank"
                        rel="noreferrer"
                        className="flex items-center gap-2 text-indigo-400 hover:underline w-fit"
                      >
                        <Globe size={12} className="shrink-0" />
                        <span>LinkedIn profile</span>
                      </a>
                    )}
                    {contact.notes && (
                      <div className="mt-2 p-2 bg-zinc-950/40 rounded border border-zinc-900 text-zinc-500 leading-relaxed max-h-12 overflow-hidden text-[10px]">
                        {contact.notes}
                      </div>
                    )}
                  </div>

                  {/* Actions */}
                  <button
                    onClick={() => deleteContact(contact.id)}
                    className="absolute top-4 right-4 text-zinc-600 hover:text-red-400 opacity-0 group-hover:opacity-100 transition-opacity duration-150 cursor-pointer"
                    title="Delete contact"
                  >
                    <Trash2 size={14} />
                  </button>
                </Card>
              </motion.div>
            ))}
          </AnimatePresence>
        </div>
      )}

      {/* Add Modal */}
      <Modal isOpen={isModalOpen} onClose={() => setIsModalOpen(false)} title="Create New Contact" size="md">
        <form onSubmit={handleCreateContact} className="space-y-4">
          <Input label="Full Name *" placeholder="Alice Vance" value={displayName} onChange={e => setDisplayName(e.target.value)} required />
          <div className="grid grid-cols-2 gap-3">
            <Input label="First Name" placeholder="Alice" value={firstName} onChange={e => setFirstName(e.target.value)} />
            <Input label="Last Name" placeholder="Vance" value={lastName} onChange={e => setLastName(e.target.value)} />
          </div>
          <Input label="Email address *" type="email" placeholder="alice@example.com" value={email} onChange={e => setEmail(e.target.value)} required />
          <Input label="Phone number" placeholder="111-222-3333" value={phone} onChange={e => setPhone(e.target.value)} />
          <div className="grid grid-cols-2 gap-3">
            <Input label="Company" placeholder="Globex Corp" value={company} onChange={e => setCompany(e.target.value)} />
            <Input label="Job Title" placeholder="Design Engineer" value={jobTitle} onChange={e => setJobTitle(e.target.value)} />
          </div>
          <Input label="LinkedIn URL" placeholder="https://linkedin.com/in/..." value={linkedinUrl} onChange={e => setLinkedinUrl(e.target.value)} />
          <Textarea label="Notes / Biography" placeholder="Internal relationship details..." value={notes} onChange={e => setNotes(e.target.value)} />
          
          <label className="flex items-center gap-2 cursor-pointer pt-2">
            <input type="checkbox" checked={isFavorite} onChange={e => setIsFavorite(e.target.checked)} className="rounded border-zinc-800 text-indigo-600 focus:ring-indigo-500" />
            <span className="text-xs text-zinc-300">Add to Favorites folder</span>
          </label>

          <div className="flex justify-end gap-3 pt-3 border-t border-zinc-850">
            <Button variant="ghost" type="button" onClick={() => setIsModalOpen(false)}>Cancel</Button>
            <Button variant="primary" type="submit">Create</Button>
          </div>
        </form>
      </Modal>

      {/* CSV Import Modal */}
      <Modal isOpen={isImportModalOpen} onClose={() => setIsImportModalOpen(false)} title="Import CSV Records" size="lg">
        <form onSubmit={handleCsvImport} className="space-y-4">
          <p className="text-xs text-zinc-400 leading-relaxed">
            Upload CSV contacts content. Standard fields like <code className="text-indigo-400">Name</code>, <code className="text-indigo-400">First Name</code>, <code className="text-indigo-400">Email</code>, and <code className="text-indigo-400">Phone</code> are mapped automatically. Duplicate records will merge without losing custom metadata.
          </p>
          <Textarea
            label="Raw CSV content"
            placeholder="Name,Email,Company,Phone&#10;Alice Smith,asmith@globex.com,Globex,111-222&#10;Bob Miller,bob@globex.com,Globex,"
            value={csvContent}
            onChange={e => setCsvContent(e.target.value)}
            className="font-mono text-xs min-h-[200px]"
            required
          />
          <div className="flex justify-end gap-3 pt-3 border-t border-zinc-850">
            <Button variant="ghost" type="button" onClick={() => setIsImportModalOpen(false)}>Cancel</Button>
            <Button variant="primary" type="submit">Import</Button>
          </div>
        </form>
      </Modal>

    </main>
  );
};

export default ContactsPage;
