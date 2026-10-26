import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { api } from '../lib/api';
import type { Contact, Phrase, Profile } from '../lib/types';

export const useMe = () => useQuery({ queryKey: ['me'], queryFn: api.me, staleTime: 30_000 });
export const useContacts = () => useQuery({ queryKey: ['contacts'], queryFn: api.contacts });
export const usePhrases = () => useQuery({ queryKey: ['phrases'], queryFn: api.phrases });
export const useCalls = () => useQuery({ queryKey: ['calls'], queryFn: api.calls });

/** The settings that matter for "was it saved?" (the server may add fields such as phone). */
const SAVED_FIELDS = ['display_name', 'preset', 'talk_modes', 'hear_modes', 'read_lang', 'type_lang', 'app_lang', 'gender', 'easy_font', 'speech_rate'] as const;
export const sameSettings = (a: Profile, b: Profile) => SAVED_FIELDS.every((k) => JSON.stringify(a[k]) === JSON.stringify(b[k]));

export function useSaveMe() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: async (p: Profile) => {
      try {
        return await api.saveMe(p);
      } catch (err) {
        // The reply can be lost (a server restart, a dropped connection) after the save went through.
        // Ask the server what it has before telling the user it failed.
        const now = await api.me().catch(() => null);
        if (now && sameSettings(now.profile, p)) return now;
        throw err;
      }
    },
    retry: 1, // saving the same settings twice is harmless
    retryDelay: 1500,
    onSuccess: (me) => qc.setQueryData(['me'], me),
  });
}

export function useConsent() {
  const qc = useQueryClient();
  return useMutation({ mutationFn: (phone?: string) => api.consent(phone), onSuccess: (me) => qc.setQueryData(['me'], me) });
}

export function useSaveContact() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: ({ contact, id }: { contact: Omit<Contact, 'id'>; id?: string }) => api.saveContact(contact, id),
    onSuccess: () => qc.invalidateQueries({ queryKey: ['contacts'] }),
  });
}

export function useDeleteContact() {
  const qc = useQueryClient();
  return useMutation({ mutationFn: api.deleteContact, onSuccess: () => qc.invalidateQueries({ queryKey: ['contacts'] }) });
}

export function useAddPhrase() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (p: Omit<Phrase, 'id'>) => api.addPhrase(p),
    onSuccess: () => qc.invalidateQueries({ queryKey: ['phrases'] }),
  });
}

export function useDeletePhrase() {
  const qc = useQueryClient();
  return useMutation({ mutationFn: api.deletePhrase, onSuccess: () => qc.invalidateQueries({ queryKey: ['phrases'] }) });
}
