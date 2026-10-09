import { ref, watch } from 'vue'
import { useRouter } from 'vue-router'
import type { TagItem } from '@/types/tag'
import type { TagSearchMode } from '@/types/search'

export type TagSearchScope = 'local' | 'remote'

const SCOPE_KEY = 'tag_search_scope'

export const TAG_SEARCH_SCOPE_OPTIONS = [
  { label: '标签·本地', value: 'local' as const },
  { label: '标签·外站', value: 'remote' as const },
]

const readScope = (): TagSearchScope =>
  localStorage.getItem(SCOPE_KEY) === 'remote' ? 'remote' : 'local'

/** 标签点击/筛选：本地搜索页或外站下载页 */
export function useTagSearchNavigate() {
  const router = useRouter()
  const scope = ref<TagSearchScope>(readScope())

  watch(scope, (v) => localStorage.setItem(SCOPE_KEY, v))

  const goLocalTagSearch = (tagIds: number[], mode: TagSearchMode = 'or') => {
    const query: Record<string, string> = { tags: tagIds.join(',') }
    if (tagIds.length > 1 && mode === 'and') query.tag_mode = 'and'
    router.push({ path: '/search', query })
  }

  const goRemoteTagSearch = (tagName: string) => {
    router.push({
      path: '/download',
      query: { q: tagName, searchType: 'tag' },
    })
  }

  const navigateByTag = (tag: TagItem, mode: TagSearchMode = 'or') => {
    if (scope.value === 'remote') goRemoteTagSearch(tag.name)
    else goLocalTagSearch([tag.id], mode)
  }

  const navigateByTagIds = (
    tagIds: number[],
    tagNameById: (id: number) => string | undefined,
    mode: TagSearchMode = 'or',
  ) => {
    if (!tagIds.length) return
    if (scope.value === 'remote') {
      const name = tagNameById(tagIds[0])
      if (name) goRemoteTagSearch(name)
      return
    }
    goLocalTagSearch(tagIds, mode)
  }

  return { scope, navigateByTag, navigateByTagIds, goRemoteTagSearch }
}
