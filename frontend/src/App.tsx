import { useState, type FormEvent } from 'react';
import './App.css';

type BlogData = {
  title: string;
  url: string;
  content: string;
  images: string[];
  image_count: number;
};

function App() {
  const [blogUrl, setBlogUrl] = useState('');
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');
  const [blogData, setBlogData] = useState<BlogData | null>(null);

  const handleSubmit = async (e: FormEvent<HTMLFormElement>) => {
    e.preventDefault();

    if (!blogUrl.trim()) return;

    setLoading(true);
    setError('');
    setBlogData(null);

    try {
      const response = await fetch('/api/scrape', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          url: blogUrl,
        }),
      });

      const result = await response.json();

      if (!response.ok) {
        throw new Error(
          result.detail || '블로그를 가져오지 못했습니다.'
        );
      }

      setBlogData(result.data);
    } catch (err) {
      setError(
        err instanceof Error ? err.message : '오류가 발생했습니다.'
      );
    } finally {
      setLoading(false);
    }
  };

  return (
    <main className="app">
      <div className="container">
        <span className="badge">BLOG TO SHORTS</span>

        <h1>블로그를 영상으로</h1>

        <p className="description">
          네이버 블로그 링크를 입력하면
          <br />
          쇼츠 영상으로 만들어 드립니다.
        </p>

        <form className="url-form" onSubmit={handleSubmit}>
          <input
            type="url"
            value={blogUrl}
            onChange={(e) => setBlogUrl(e.target.value)}
            placeholder="네이버 블로그 URL을 입력하세요"
            required
          />

          <button type="submit" disabled={loading}>
            {loading ? '분석 중...' : '시작하기 →'}
          </button>
        </form>

        {error && (
          <p style={{ color: 'red', marginTop: 20 }}>
            {error}
          </p>
        )}

        {blogData && (
          <section style={{ marginTop: 48, textAlign: 'left' }}>
            <h2>{blogData.title}</h2>

            <p>이미지 {blogData.image_count}개 추출</p>

            <div
              style={{
                whiteSpace: 'pre-wrap',
                marginTop: 24,
                lineHeight: 1.8,
              }}
            >
              {blogData.content}
            </div>

            <div
              style={{
                display: 'grid',
                gridTemplateColumns: 'repeat(3, 1fr)',
                gap: 12,
                marginTop: 24,
              }}
            >
              {blogData.images.map((image, index) => (
                <img
                  key={index}
                  src={image}
                  alt={`블로그 이미지 ${index + 1}`}
                  referrerPolicy="no-referrer"
                  style={{
                    width: '100%',
                    borderRadius: 8,
                  }}
                />
              ))}
            </div>
          </section>
        )}
      </div>
    </main>
  );
}

export default App;