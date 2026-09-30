"""Common function words, ignored when deciding which sentences matter."""

EN = frozenset("""
a about above after again against all almost also although always am among an and another any anyone
anything are aren't around as at be became because become becomes been before being below between both
but by can cannot could couldn't did didn't do does doesn't doing don't done down during each either
else enough etc even ever every few for from further get gets given gives go going got had hadn't has
hasn't have haven't having he her here hers herself him himself his how however i if in into is isn't
it it's its itself just last least less let like made make makes many may me might more most much must
my myself neither never no nor not now of off often on once one only onto or other others otherwise
our ours ourselves out over own per perhaps please put rather really said same say says see seen shall
she should shouldn't since so some something still such than that that's the their theirs them
themselves then there there's therefore these they this those though through thus to too toward
towards under until up upon us use used uses using very via was wasn't we well were weren't what
when where whereas whether which while who whom whose why will with within without would wouldn't yet
you your yours yourself yourselves also however hereby herein hereof hereto thereof therein
""".split())

TR = frozenset("""
acaba ama ancak aslında az bana bazen bazı bazıları belki ben beni benim beri bile bir birçok biri
birkaç birkez birşey birşeyi biz bize bizi bizim bu buna bunda bundan bunlar bunları bunların bunu
bunun burada böyle böylece çok çünkü da daha dahi de defa değil diğer diğeri diye dolayı dolayısıyla
edecek eden ederek edilecek ediliyor edilmesi ediyor eğer elbette en etmesi etti ettiği ettiğini fakat
gibi göre halen hangi hatta hem henüz hep hepsi her herhangi herkes hiç hiçbir için ile ilgili ise
işte itibaren itibariyle kadar karşın kendi kendine kendini kez ki kim kimden kime kimi kimse
mı mi mu mü nasıl ne neden nedenle nerde nerede nereye niye niçin o olan olarak oldu olduğu olduğunu
olmadı olmak olması olmayan olmaz olsa olsun olup olur olursa oluyor on ona ondan onlar onlardan
onları onların onu onun orada öyle oysa pek rağmen sadece sanki sen siz sizi sizin şey şeyden şeyi
şeyler şöyle şu şuna şunda şundan şunları şunu tarafından tüm üzere var vardı ve veya ya yani yapacak
yapılan yapılması yapıyor yapmak yaptı yaptığı yaptığını yerine yine yoksa zaten şayet ayrıca
dair olacak olacaktır olmuştur olmaktadır bulunan bulunmaktadır edilir edilen
""".split())

BY_LANGUAGE = {"en": EN, "tr": TR}
