ThisBuild / organization := "dadao"
ThisBuild / version := "0.1.0"
ThisBuild / scalaVersion := "2.13.16"

lazy val root = (project in file("."))
  .settings(
    name := "dadao-rtl",
    // Chipyard integration sources are compiled by the Chipyard `dadao`
    // project, which supplies the rocket-chip classpath.
    Compile / unmanagedSources := {
      val chipyardIntegration = Set(
        "DADAOTile.scala",
        "DADAOConfig.scala",
        "DADAOElaborator.scala"
      )
      (Compile / unmanagedSources).value.filterNot { source =>
        chipyardIntegration.contains(source.getName)
      }
    },
    libraryDependencies ++= Seq(
      "org.chipsalliance" %% "chisel" % "6.7.0",
      "edu.berkeley.cs" %% "chiseltest" % "6.0.0" % Test
    ),
    addCompilerPlugin(
      "org.chipsalliance" % "chisel-plugin" % "6.7.0" cross CrossVersion.full
    ),
    Test / parallelExecution := false
  )
