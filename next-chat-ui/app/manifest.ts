import { MetadataRoute } from 'next'

export default function manifest(): MetadataRoute.Manifest {
  return {
    name: '藤花歯科クリニック 専用AI助手',
    short_name: '藤花AI助手',
    description: '藤花歯科クリニックの資料・マニュアルを検索・要約する専用AI助手',
    start_url: '/',
    display: 'standalone',
    background_color: '#ffffff',
    theme_color: '#10b981', // emerald-600
    icons: [
      {
        src: '/icon.png',
        sizes: '512x512',
        type: 'image/png',
      },
    ],
  }
}
