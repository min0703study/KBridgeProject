from kiwipiepy import Kiwi

kiwi = Kiwi()
result = kiwi.analyze("무궁화꽃이피었습니다.")
print(result)

from kiwipiepy import Kiwi

kiwi = Kiwi()
result = kiwi.analyze("안녕하세요 형태소 분석기 키위입니다.")
print(result)

print(f"result = {result}")
# print(len(result), type(result))
# print("="*50)
# print(f"result[0] = {result[0]}")
# print(len(result[0]), type(result[0]))
# print("="*50)
# print(f"result[0][0] = {result[0][0]}")   # res
# print(f"result[0][1] = {result[0][1]}")   # score
print("="*50)
# print(f"result[0][0]의 타입: {type(result[0][0])}, result[0][1]의 길이: {len(result[0][0])}")
# 반복 변수 정의 : word
# 반복 출력: result에서 하나씩 뽑아서 word에 담은 후 차례대로 출력
# 조건
for res, score in result:
    print(f"res = {res}")
    for r in res:
        if r.tag[0] == "N":
            print(f"r = {r}")
            print(f"form = {r.form}, tag = {r.tag}")
            print("-"*50)

from kiwipiepy import Kiwi

kiwi = Kiwi()

text = "안녕하세요. 저는 형태소 분석기 입니다."

result = kiwi.analyze(text)
print(result)
print(len(result))
print("="*50)
# analyze 함수의 결과는 1개의 요소(튜플)를 가지고 있다.
result_0 = result[0]
print(result_0)
print(len(result_0))
print("="*50)
# 튜플 안에는 요소가 2개 있다.
print(result_0[0]) # 내가 필요한거 여기 있다.
print(result_0[1])
final_result = result_0[0]
print("="*50)
print(final_result)
print(len(final_result))

# 명사인 단어만 추출해서 noun_list에 저장하기
## kiwi에서 명사는 tag가 N으로 시작한다.
## 조건 표현 방법 1 - tag[0] == "N"  표현 방법 2 - tag.startswith("N")
noun_list = []
for res in final_result:
    form = res.form
    tag = res.tag
    if tag.startswith("N"):
        noun_list.append(form)
        print(res)
        print(f"form={form}, tag={tag}")
print("="*100)
print(noun_list)

from kiwipiepy import Kiwi

kiwi = Kiwi()

text = "안녕하세요. 저는 형태소 분석기 입니다."

result = kiwi.tokenize(text)
print(result)