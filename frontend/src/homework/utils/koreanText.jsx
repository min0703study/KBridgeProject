import React from 'react'

const semanticLineMap = {
  '날씨가 어떻습니까?': ['날씨가', '어떻습니까?'],
  '오늘 날씨가 어때요?': ['오늘 날씨가', '어때요?'],
  '서울은 오늘 날씨가 어때요?': ['서울은 오늘', '날씨가 어때요?'],
  '한국어 공부는 어렵지만 재미있어요.': ['한국어 공부는', '어렵지만 재미있어요.'],
  '한국어 공부는 어렵지만 재미있어요': ['한국어 공부는', '어렵지만 재미있어요'],
  '눈이 오고 춥습니다.': ['눈이 오고', '춥습니다.'],
  '친구하고 영화를 봐요.': ['친구하고', '영화를 봐요.'],
  '어제 뭐 했어요?': ['어제', '뭐 했어요?'],
  '오늘이 무슨 요일이에요?': ['오늘이', '무슨 요일이에요?'],
}

const romanizationMap = {
  '감사합니다.': 'gamsahamnida.',
  '아니요, 괜찮아요.': 'aniyo, gwaenchanayo.',
  '영수증 필요하세요?': 'yeongsujeung piryo haseyo?',
  '필리핀 사람이에요.': 'Pillipin saramieyo.',
  '안녕하세요.': 'annyeonghaseyo.',
  '저는 마리아예요.': 'jeoneun Mariayeyo.',
  '물': 'mul',
  '주세요.': 'juseyo.',
  '사전 주세요.': 'sajeon juseyo.',
  '이거는 뭐예요?': 'igeoneun mwoyeyo?',
  '사전이에요.': 'sajeonieyo.',
  '학교에': 'hakgyoe',
  '가요.': 'gayo.',
  '학교에 가요.': 'hakgyoe gayo.',
  '오늘은 안 가요.': 'oneureun an gayo.',
  '어디에 가요?': 'eodie gayo?',
  '같이 가요.': 'gachi gayo.',
  '도서관 앞에 있어요.': 'doseogwan ape isseoyo.',
  '도서관 앞에': 'doseogwan ape',
  '있어요.': 'isseoyo.',
  '어디에 있어요?': 'eodie isseoyo?',
  '오늘': 'oneul',
  '날씨가': 'nalssiga',
  '어때요?': 'eottaeyo?',
  '서울은 오늘 날씨가 어때요?': 'Seoureun oneul nalssiga eottaeyo?',
  '더워요. 도쿄도 더워요?': 'deowoyo. Dokyodo deowoyo?',
  '아니요. 어제는 더웠지만 오늘은 안 더워요.': 'aniyo. eojeneun deowotjiman oneureun an deowoyo.',
  '재미있어요': 'jaemiisseoyo',
  '한국어 공부는': 'hangugeo gongbuneun',
  '어렵지만': 'eoryeopjiman',
  '눈이 오고': 'nuni ogo',
  '춥습니다': 'chupseumnida',
  '봄': 'bom',
  '겨울': 'gyeoul',
  '계절': 'gyejeol',
  '날씨': 'nalssi',
  '금요일이에요. 금요일에 파티가 있어요.': 'geumyoirieyo. geumyoire patiga isseoyo.',
  '5월 9일에 시간이 있어요?': 'owol gu ire sigani isseoyo?',
  '아, 미안해요. 금요일에는 약속이 있어요.': 'a, mianhaeyo. geumyoireneun yaksogi isseoyo.',
  '9일이 무슨 요일이에요?': 'gu iri museun yoirieyo?',
  '주말에 뭐 했어요?': 'jumare mwo haesseoyo?',
  '친구하고 같이 영화 보고 쇼핑했어요.': 'chinguhago gachi yeonghwa bogo syopinghaesseoyo.',
  '어제 뭐 했어요?': 'eoje mwo haesseoyo?',
  '코엑스몰에 갔어요.': 'Koekseumore gasseoyo.',
  '한강에서 타요.': 'Hangangeseo tayo.',
  '그럼 주말에 같이 자전거 탈까요?': 'geureom jumare gachi jajeongeo talkkayo?',
  '켈리 씨, 한국 생활이 어때요?': 'Kelly ssi, hanguk saenghwari eottaeyo?',
  '좋아요. 어디에서 탈까요?': 'joayo. eodieseo talkkayo?',
  '한국어 공부는 재미있지만 주말에는 조금 심심해요.': 'hangugeo gongbuneun jaemiitjiman jumareneun jogeum simsimhaeyo.',
  '며칠이에요?': 'myeochirieyo?',
  '오늘이': 'oneuri',
  '구 일이에요.': 'gu irieyo.',
  '오월': 'owol',
  '요일이에요?': 'yoirieyo?',
  '무슨': 'museun',
  '해요?': 'haeyo?',
  '토요일에': 'toyoire',
  '뭐': 'mwo',
  '영화를': 'yeonghwareul',
  '봐요.': 'bwayo.',
  '친구하고': 'chinguhago',
  '했어요?': 'haesseoyo?',
  '어제': 'eoje',
  '쇼핑했어요.': 'syopinghaesseoyo.',
  '친구하고 같이': 'chinguhago gachi',
  '영화 보고': 'yeonghwa bogo',
  '김밥 하나': 'gimbap hana',
  '자전거': 'jajeongeo',
  '영화 볼까요?': 'yeonghwa bolkkayo?',
  '주말에 같이': 'jumare gachi',
}

function splitBalanced(text) {
  const words = String(text ?? '').trim().split(/\s+/).filter(Boolean)
  if (words.length <= 1) return [String(text ?? '')]
  if (words.length === 2) return words

  const mid = Math.ceil(words.length / 2)
  return [words.slice(0, mid).join(' '), words.slice(mid).join(' ')]
}

export function semanticLines(text) {
  const normalized = String(text ?? '').trim()
  if (!normalized) return ['']
  return semanticLineMap[normalized] ?? splitBalanced(normalized)
}

export function SemanticText({ text, as: Tag = 'span', className = '', singleLine = false }) {
  if (singleLine) {
    return (
      <Tag className={`semantic-text semantic-text-single-line ${className}`.trim()}>
        {text}
      </Tag>
    )
  }

  const lines = semanticLines(text)

  return (
    <Tag className={`semantic-text ${className}`.trim()}>
      {lines.map((line, index) => (
        <React.Fragment key={`${line}-${index}`}>
          {index > 0 ? <br /> : null}
          <span>{line}</span>
        </React.Fragment>
      ))}
    </Tag>
  )
}

export function KoreanWithRomanization({ text, as: Tag = 'span', className = '' }) {
  const romanization = romanizationMap[String(text ?? '').trim()]

  return (
    <Tag className={`korean-romanized ${className}`.trim()}>
      <span className="korean-line">{text}</span>
      {romanization ? <small>{romanization}</small> : null}
    </Tag>
  )
}
