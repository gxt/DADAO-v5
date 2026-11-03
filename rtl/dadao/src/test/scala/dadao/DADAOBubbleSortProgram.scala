package dadao

private[dadao] object DADAOBubbleSortProgram {
  val initialValues: Seq[BigInt] = Seq(
    5, 1, 4, 2, 3
  )
  val expectedValues: Seq[BigInt] = Seq(
    1, 2, 3, 4, 5
  )
  val words: Seq[BigInt] = Seq(
    BigInt("4c040005", 16), BigInt("4c080001", 16), BigInt("4c0c0004", 16), BigInt("4c100002", 16),
    BigInt("4c140003", 16), BigInt("40a87042", 16), BigInt("6d1c0004", 16), BigInt("40b06041", 16),
    BigInt("40b01081", 16), BigInt("40b02181", 16), BigInt("40a87083", 16), BigInt("6d1c0004", 16),
    BigInt("40b06081", 16), BigInt("40b020c1", 16), BigInt("40b03181", 16), BigInt("40a870c4", 16),
    BigInt("6d1c0004", 16), BigInt("40b060c1", 16), BigInt("40b03101", 16), BigInt("40b04181", 16),
    BigInt("40a87105", 16), BigInt("6d1c0004", 16), BigInt("40b06101", 16), BigInt("40b04141", 16),
    BigInt("40b05181", 16), BigInt("40a87042", 16), BigInt("6d1c0004", 16), BigInt("40b06041", 16),
    BigInt("40b01081", 16), BigInt("40b02181", 16), BigInt("40a87083", 16), BigInt("6d1c0004", 16),
    BigInt("40b06081", 16), BigInt("40b020c1", 16), BigInt("40b03181", 16), BigInt("40a870c4", 16),
    BigInt("6d1c0004", 16), BigInt("40b060c1", 16), BigInt("40b03101", 16), BigInt("40b04181", 16),
    BigInt("40a87042", 16), BigInt("6d1c0004", 16), BigInt("40b06041", 16), BigInt("40b01081", 16),
    BigInt("40b02181", 16), BigInt("40a87083", 16), BigInt("6d1c0004", 16), BigInt("40b06081", 16),
    BigInt("40b020c1", 16), BigInt("40b03181", 16), BigInt("40a87042", 16), BigInt("6d1c0004", 16),
    BigInt("40b06041", 16), BigInt("40b01081", 16), BigInt("40b02181", 16), BigInt("19042000", 16),
    BigInt("19082002", 16), BigInt("190c2004", 16), BigInt("19102006", 16), BigInt("19142008", 16),
    BigInt("11202000", 16), BigInt("11242002", 16), BigInt("11282004", 16), BigInt("112c2006", 16),
    BigInt("11302008", 16), BigInt("47880000", 16),
  )
}
