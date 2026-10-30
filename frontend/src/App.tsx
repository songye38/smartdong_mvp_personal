import { useState, type FormEvent } from 'react';
import './App.css';

type BlogSection = {
  id: string;
  image_url: string | null;
  extra_images: string[];
  text: string;
};

type BlogData = {
  title: string;
  url: string;
  content: string;
  images: string[];
  image_count: number;
  sections: BlogSection[];
  section_count: number;
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
          <section className="blog-result">

            <div className="blog-result__header">
              <h2>{blogData.title}</h2>

              <p>
                총 {blogData.section_count}개 단락 ·
                이미지 {blogData.image_count}개
              </p>
            </div>

            <div className="blog-sections">

              {blogData.sections.map((section) => (
                <article
                  key={section.id}
                  className="blog-section"
                >

                  <div className="blog-section__header">
                    <span>{section.id.toUpperCase()}</span>

                    {section.image_url === null && (
                      <span className="blog-section__intro">
                        도입부
                      </span>
                    )}
                  </div>

                  {section.image_url && (
                    <div className="blog-section__image">
                      <img
                        src={section.image_url}
                        alt={`${section.id} 대표 이미지`}
                        referrerPolicy="no-referrer"
                      />
                    </div>
                  )}

                  {section.extra_images.length > 0 && (
                    <div className="blog-section__extras">

                      <p>
                        여분 이미지 {section.extra_images.length}개
                      </p>

                      <div className="blog-section__extra-grid">
                        {section.extra_images.map((image, index) => (
                          <img
                            key={`${section.id}-${index}`}
                            src={image}
                            alt={`여분 이미지 ${index + 1}`}
                            referrerPolicy="no-referrer"
                          />
                        ))}
                      </div>

                    </div>
                  )}

                  <div className="blog-section__text">
                    {section.text || '연결된 텍스트가 없습니다.'}
                  </div>

                </article>
              ))}

            </div>
          </section>
        )}
      </div>
    </main>
  );
}

export default App;