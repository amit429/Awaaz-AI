import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { api } from '../lib/api';
import type { Contact, Phrase, Profile } from '../lib/types';

export const useMe = () => useQuery({ queryKey: ['me'], queryFn: api.me, staleTime: 30_000 });
export const useContacts = () => useQuery({ queryKey: ['contacts'], queryFn: api.contacts });
export const usePhrases = () => useQuery({ queryKey: ['phrases'], queryFn: api.phrases });
export const useCalls = () => useQuery({ queryKey: ['calls'], queryFn: api.calls });

export function useSaveMe() {
  const qc = useQueryClient();
  return useMutation({ mutationFn: (p: Profile) => api.saveMe(p), onSuccess: (me) => qc.setQueryData(['me'], me) });
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
